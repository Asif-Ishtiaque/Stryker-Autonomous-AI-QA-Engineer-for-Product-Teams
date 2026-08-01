"""Web platform Executor — the reference implementation of the Executor
plugin interface. Runs a PlannedStep against a real Playwright page using
self-healing locators, capturing evidence for every step regardless of
outcome (evidence-on-failure only would hide near-misses).
"""
from __future__ import annotations

import asyncio
import time
from typing import Any
from urllib.parse import urljoin

from playwright.async_api import Page

from app.agents.executors.base import Executor, StepEventSink
from app.agents.executors.web.locator_engine import SelfHealingLocator, Target
from app.agents.executors.web.screencast import start_screencast
from app.agents.state import ExecutedStepResult, PlannedStep
from app.core.logging import get_logger
from app.evidence.capture import (
    capture_accessibility_tree,
    capture_console_logs,
    capture_dom_snapshot,
    capture_network_logs,
    capture_screenshot,
    capture_timing,
)
from app.execution.browser_pool import get_browser_pool

logger = get_logger(__name__)


class WebExecutor(Executor):
    platform = "web"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._context_cm = None
        self._context = None
        self._page: Page | None = None
        self._console_buffer: list[dict[str, Any]] = []
        self._network_buffer: list[dict[str, Any]] = []
        self._stop_screencast: Any = None

    async def setup(self) -> None:
        pool = get_browser_pool()
        extra_headers = (self.credential or {}).get("headers") or {}
        self._context_cm = pool.acquire_context(
            ignore_https_errors=True,
            record_video_dir=None,  # per-run video recording is enabled per-step below via CDP if needed
            extra_http_headers=extra_headers or None,
        )
        self._context = await self._context_cm.__aenter__()
        self._page = await self._context.new_page()
        self._page.on("console", self._on_console)
        self._page.on("requestfinished", self._on_request_finished)
        if self.credential and self.credential.get("cookies"):
            # Stored as a simple {name: value} map (see CredentialCreate.cookies);
            # Playwright needs the richer {name, value, url} shape to know which
            # domain to attach each cookie to, so expand against base_url here.
            cookie_list = [
                {"name": name, "value": value, "url": self.base_url}
                for name, value in self.credential["cookies"].items()
            ]
            await self._context.add_cookies(cookie_list)

        if self.run_id is not None:
            try:
                self._stop_screencast = await start_screencast(self._page, self.run_id)
            except Exception as exc:  # noqa: BLE001 — Mission Control's live video is a bonus,
                # never a reason to fail the run itself.
                logger.warning("web_executor.screencast_start_failed", error=str(exc))

    def _on_console(self, msg: Any) -> None:
        entry = {"type": msg.type, "text": msg.text}
        self._console_buffer.append(entry)
        asyncio.ensure_future(self.on_event({"run_status": "running", "console": entry}))

    def _on_request_finished(self, req: Any) -> None:
        entry = {"url": req.url, "method": req.method}
        self._network_buffer.append(entry)
        asyncio.ensure_future(self.on_event({"run_status": "running", "network": entry}))

    async def teardown(self) -> None:
        try:
            if self._stop_screencast:
                await self._stop_screencast()
            if self._page:
                await self._page.close()
        finally:
            if self._context_cm:
                await self._context_cm.__aexit__(None, None, None)

    async def execute_step(self, step: PlannedStep) -> ExecutedStepResult:
        assert self._page is not None, "setup() must be called before execute_step()"
        started = time.monotonic()
        evidence_refs: list[dict[str, Any]] = []
        target_desc = step.get("parameters", {}).get("description") or step["name"]
        await self.on_event(
            {"run_status": "running", "sequence": step["sequence"], "reasoning": f"{step['action_type']} — {target_desc}"}
        )
        try:
            result = await self._dispatch(step)
            status = "passed"
            error_message = None
        except Exception as exc:  # noqa: BLE001 — a failed step is a normal outcome, not a bug
            status = "failed"
            error_message = str(exc)
            result = {}
            logger.warning("web_executor.step_failed", step=step["name"], error=str(exc))

        await self.on_event(
            {
                "run_status": "running",
                "sequence": step["sequence"],
                "reasoning": f"{'done' if status == 'passed' else 'failed'}: {step['name']}"
                + (f" — {error_message}" if error_message else ""),
            }
        )

        evidence_refs.append(await capture_screenshot(self._page, f"runs/{step['sequence']}"))
        evidence_refs.append(await capture_dom_snapshot(self._page, f"runs/{step['sequence']}"))
        evidence_refs.append(await capture_accessibility_tree(self._page))
        evidence_refs.append(capture_console_logs(self._console_buffer[-50:]))
        evidence_refs.append(capture_network_logs(self._network_buffer[-50:]))
        evidence_refs.append(capture_timing({"duration_ms": int((time.monotonic() - started) * 1000)}))

        return ExecutedStepResult(
            sequence=step["sequence"],
            status=status,
            result=result,
            error_message=error_message,
            evidence_refs=evidence_refs,
        )

    async def _dispatch(self, step: PlannedStep) -> dict[str, Any]:
        action = step["action_type"]
        params = step["parameters"]
        page = self._page
        assert page is not None

        if action == "navigate":
            url = params.get("url", "")
            full_url = url if url.startswith("http") else urljoin(self.base_url, url)
            await page.goto(full_url, wait_until="domcontentloaded")
            return {"url": page.url}

        if action == "login":
            return await self._login(params)

        if action in ("click", "fill", "select", "check", "uncheck", "hover"):
            locator = await self._resolve(params)
            if action == "click":
                await locator.click()
            elif action == "fill":
                await locator.fill(params.get("value", ""))
            elif action == "select":
                await locator.select_option(params.get("value", ""))
            elif action == "check":
                await locator.check()
            elif action == "uncheck":
                await locator.uncheck()
            elif action == "hover":
                await locator.hover()
            return {"action": action, "target": params.get("description")}

        if action == "wait":
            await page.wait_for_timeout(int(params.get("ms", 1000)))
            return {"waited_ms": params.get("ms", 1000)}

        if action == "assert_text":
            text = params.get("text", "")
            locator = page.get_by_text(text, exact=False).first
            await locator.wait_for(state="visible", timeout=params.get("timeout_ms", 10000))
            return {"found_text": text}

        if action == "assert_business_outcome":
            # The heavy lifting (deciding WHETHER the outcome was actually met)
            # happens in the ValidatorAgent using this step's evidence — this
            # action just guarantees a fresh screenshot/DOM snapshot exists to
            # validate against.
            return {"marker": "business_outcome_checkpoint", "expected": step.get("expected_outcome")}

        raise ValueError(f"Unsupported web action_type: {action}")

    async def _resolve(self, params: dict[str, Any]):
        target = Target(
            description=params.get("description", ""),
            role=params.get("role"),
            text_hint=params.get("text_hint"),
            test_id_hint=params.get("test_id_hint"),
        )
        locator_engine = SelfHealingLocator(self._page, self.llm)  # type: ignore[arg-type]
        result = await locator_engine.locate(target)
        if result.locator is None:
            raise RuntimeError(
                f"Could not locate element for '{target.description}' after trying: {result.attempts}"
            )
        return result.locator

    async def _login(self, params: dict[str, Any]) -> dict[str, Any]:
        if not self.credential:
            raise RuntimeError("login step requested but no credential profile was attached to this run")
        page = self._page
        assert page is not None
        await page.goto(urljoin(self.base_url, params.get("login_path", "/login")), wait_until="domcontentloaded")

        username = self.credential.get("username")
        password = self.credential.get("password")
        if username:
            engine = SelfHealingLocator(page, self.llm)  # type: ignore[arg-type]
            username_target = Target(description="username or email field", role="textbox", text_hint="email")
            loc = await engine.locate(username_target)
            if loc.locator:
                await loc.locator.fill(username)
        if password:
            engine = SelfHealingLocator(page, self.llm)  # type: ignore[arg-type]
            password_target = Target(description="password field", role="textbox", text_hint="password")
            loc = await engine.locate(password_target)
            if loc.locator:
                await loc.locator.fill(password)

        engine = SelfHealingLocator(page, self.llm)  # type: ignore[arg-type]
        submit = await engine.locate(Target(description="sign in / log in / submit button", role="button", text_hint="log in"))
        if submit.locator:
            await submit.locator.click()
            await page.wait_for_load_state("domcontentloaded")
        return {"logged_in_as": username}
