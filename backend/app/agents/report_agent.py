"""ReportAgent — turns the finished RunState into a professional Markdown
narrative (the JSON/PDF/Jira renderings in app.reports are pure functions of
this same state, no separate LLM call needed).
"""
from __future__ import annotations

from app.agents.state import RunState
from app.llm.base import ChatMessage, LLMProvider

SYSTEM_PROMPT = """You are writing a QA report for a Product Manager audience — clear, concise,
no automation jargon. Structure the report as:

## Executive Summary
One paragraph: what was tested, the outcome, and the confidence score.

## Requirement
Restate the requirement and what it implies.

## Timeline
A short numbered list of what was executed.

## Findings
For each validation finding, state whether it was met/not met/inconclusive and why.

## Root Cause (only if failed)
The hypothesis, in plain language.

## Recommendation
One or two sentences on what to do next.

Use Markdown. Be specific — reference actual outcomes and evidence, not generic language."""


async def run_report_agent(state: RunState, llm: LLMProvider) -> RunState:
    user_prompt = (
        f"Requirement: {state.get('requirement_text')}\n"
        f"Understood intent: {state.get('understood_intent')}\n"
        f"Final status: {state.get('final_status')}\n"
        f"Confidence score: {state.get('confidence_score')}\n"
        f"Severity: {state.get('severity')}\n"
        f"Root cause hypothesis: {state.get('root_cause_hypothesis')}\n"
        f"Validation findings: {state.get('validation_findings')}\n"
        f"Plan: {state.get('plan')}\n"
        f"Step results: {state.get('step_results')}\n"
    )
    markdown = await llm.chat(
        [ChatMessage(role="system", content=SYSTEM_PROMPT), ChatMessage(role="user", content=user_prompt)]
    )

    report_json = {
        "requirement_text": state.get("requirement_text"),
        "understood_intent": state.get("understood_intent"),
        "final_status": state.get("final_status"),
        "confidence_score": state.get("confidence_score"),
        "severity": state.get("severity"),
        "root_cause_hypothesis": state.get("root_cause_hypothesis"),
        "expected_outcomes": state.get("expected_outcomes"),
        "inferred_validations": state.get("inferred_validations"),
        "identified_risks": state.get("identified_risks"),
        "predicted_edge_cases": state.get("predicted_edge_cases"),
        "validation_findings": state.get("validation_findings"),
        "plan": state.get("plan"),
        "step_results": state.get("step_results"),
    }

    return {**state, "report_markdown": markdown, "report_json": report_json}
