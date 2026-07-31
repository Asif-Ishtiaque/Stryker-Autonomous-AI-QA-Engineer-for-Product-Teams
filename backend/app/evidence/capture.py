"""Evidence capture helpers used by executors while a step runs.

Every capture returns a plain dict ready to become an Evidence row —
{evidence_type, storage_key|inline_data, content_type} — so executors never
touch MinIO or the DB directly; they just call these and append the result
to ExecutedStepResult.evidence_refs.
"""
from __future__ import annotations

from typing import Any

from playwright.async_api import Page

from app.evidence.storage import get_evidence_storage


async def capture_screenshot(page: Page, key_prefix: str) -> dict[str, Any]:
    data = await page.screenshot(full_page=True, type="png")
    key = get_evidence_storage().put_bytes(key_prefix, data, "image/png", ".png")
    return {"evidence_type": "screenshot", "storage_key": key, "content_type": "image/png"}


async def capture_dom_snapshot(page: Page, key_prefix: str) -> dict[str, Any]:
    html = await page.content()
    key = get_evidence_storage().put_bytes(key_prefix, html.encode(), "text/html", ".html")
    return {"evidence_type": "dom_snapshot", "storage_key": key, "content_type": "text/html"}


async def capture_accessibility_tree(page: Page) -> dict[str, Any]:
    tree = await page.accessibility.snapshot(interesting_only=True)
    return {"evidence_type": "accessibility_tree", "inline_data": tree or {}, "content_type": "application/json"}


def capture_console_logs(buffer: list[dict[str, Any]]) -> dict[str, Any]:
    return {"evidence_type": "console_log", "inline_data": {"entries": buffer}, "content_type": "application/json"}


def capture_network_logs(buffer: list[dict[str, Any]]) -> dict[str, Any]:
    return {"evidence_type": "network_log", "inline_data": {"entries": buffer}, "content_type": "application/json"}


def capture_timing(timing: dict[str, Any]) -> dict[str, Any]:
    return {"evidence_type": "timing", "inline_data": timing, "content_type": "application/json"}
