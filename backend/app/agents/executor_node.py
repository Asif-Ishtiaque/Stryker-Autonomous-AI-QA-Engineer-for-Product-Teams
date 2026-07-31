"""Graph node that drives a platform Executor through the PlannerAgent's plan.

This is the seam between the platform-agnostic agent pipeline and a specific
Executor plugin — it knows nothing about Playwright, HTTP, or Appium; it
only knows the Executor ABC (setup / execute_step / teardown) and the
step-event callback used to stream live progress to the frontend.
"""
from __future__ import annotations

from app.agents.executors import get_executor_class
from app.agents.state import RunState
from app.core.logging import get_logger
from app.llm.base import LLMProvider

logger = get_logger(__name__)


async def run_executor_node(state: RunState, llm: LLMProvider, on_event) -> RunState:
    executor_cls = get_executor_class(state["platform"])
    executor = executor_cls(state["base_url"], state.get("credential"), on_event, llm)

    step_results = []
    execution_error: str | None = None

    await executor.setup()
    try:
        for step in state.get("plan", []):
            await on_event(
                {
                    "run_status": "running",
                    "step_status": "running",
                    "sequence": step["sequence"],
                    "name": step["name"],
                }
            )
            try:
                result = await executor.execute_step(step)
            except Exception as exc:  # noqa: BLE001 — an unrecoverable step still yields a report
                logger.error("executor_node.step_crashed", step=step["name"], error=str(exc))
                result = {
                    "sequence": step["sequence"],
                    "status": "failed",
                    "result": {},
                    "error_message": str(exc),
                    "evidence_refs": [],
                }
            step_results.append(result)
            await on_event(
                {
                    "run_status": "running",
                    "step_status": result["status"],
                    "sequence": step["sequence"],
                    "name": step["name"],
                    "message": result.get("error_message"),
                }
            )
            if result["status"] == "failed" and step.get("action_type") in ("login", "navigate"):
                # A failed login/navigation makes every subsequent step meaningless —
                # stop early rather than burning through the rest of the plan.
                execution_error = f"Step '{step['name']}' failed: {result.get('error_message')}"
                break
    finally:
        await executor.teardown()

    return {**state, "step_results": step_results, "execution_error": execution_error}
