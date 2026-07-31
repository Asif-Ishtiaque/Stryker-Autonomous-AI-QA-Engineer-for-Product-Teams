"""LangGraph wiring for the end-to-end run pipeline:

    RequirementAgent -> PlannerAgent -> Executor -> ValidatorAgent
        -> ComparatorAgent -> ReportAgent

A conditional edge sends control back to PlannerAgent (up to
`max_plan_retries`) when execution errors out entirely (e.g. login failed),
since a fresh plan — not a repeat of the same broken one — is the more
useful retry. Per-step retries happen inside the Executor, not here.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

from langgraph.graph import END, StateGraph

from app.agents.comparator_agent import run_comparator_agent
from app.agents.executor_node import run_executor_node
from app.agents.planner_agent import run_planner_agent
from app.agents.report_agent import run_report_agent
from app.agents.requirement_agent import run_requirement_agent
from app.agents.state import RunState
from app.agents.validator_agent import run_validator_agent
from app.core.config import get_settings
from app.llm.base import LLMProvider

EventSink = Callable[[dict[str, Any]], Awaitable[None]]


def build_run_graph(llm: LLMProvider, on_event: EventSink):
    settings = get_settings()

    async def requirement_node(state: RunState) -> RunState:
        await on_event({"run_status": "planning", "message": "Understanding requirement"})
        return await run_requirement_agent(state, llm)

    async def planner_node(state: RunState) -> RunState:
        await on_event({"run_status": "planning", "message": "Generating execution plan"})
        return await run_planner_agent(state, llm)

    async def executor_node(state: RunState) -> RunState:
        return await run_executor_node(state, llm, on_event)

    async def validator_node(state: RunState) -> RunState:
        await on_event({"run_status": "validating", "message": "Validating business outcomes"})
        return await run_validator_agent(state, llm)

    async def comparator_node(state: RunState) -> RunState:
        return await run_comparator_agent(state, llm)

    async def report_node(state: RunState) -> RunState:
        return await run_report_agent(state, llm)

    def should_replan(state: RunState) -> str:
        retries = state.get("plan_retry_count", 0)
        if state.get("execution_error") and retries < settings.max_plan_retries:
            return "replan"
        return "continue"

    async def bump_retry(state: RunState) -> RunState:
        return {**state, "plan_retry_count": state.get("plan_retry_count", 0) + 1}

    graph = StateGraph(RunState)
    graph.add_node("requirement", requirement_node)
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("bump_retry", bump_retry)
    graph.add_node("validator", validator_node)
    graph.add_node("comparator", comparator_node)
    graph.add_node("report", report_node)

    graph.set_entry_point("requirement")
    graph.add_edge("requirement", "planner")
    graph.add_edge("planner", "executor")
    graph.add_conditional_edges("executor", should_replan, {"replan": "bump_retry", "continue": "validator"})
    graph.add_edge("bump_retry", "planner")
    graph.add_edge("validator", "comparator")
    graph.add_edge("comparator", "report")
    graph.add_edge("report", END)

    return graph.compile()
