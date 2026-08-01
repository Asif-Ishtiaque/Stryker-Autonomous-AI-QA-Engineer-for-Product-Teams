"""ComparatorAgent — reduces validation findings + execution outcome into a
single confidence score, severity, final status, and (on failure) a root
cause hypothesis a developer can act on immediately.

The confidence score is computed deterministically from the findings rather
than asked of the LLM directly, so it's reproducible and auditable; the LLM
is only used for the qualitative root-cause narrative when something failed.
"""
from __future__ import annotations

import json

from app.agents.state import RunState
from app.llm.base import ChatMessage, LLMProvider, parse_json_object

ROOT_CAUSE_SCHEMA = {
    "type": "object",
    "properties": {
        "root_cause_hypothesis": {"type": "string"},
        "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
    },
    "required": ["root_cause_hypothesis", "severity"],
}

ROOT_CAUSE_SYSTEM_PROMPT = """You are a senior engineer triaging a failed QA run. Given the requirement,
the step that failed (or the business outcome that was not met), and the evidence gathered, write a
one-to-three sentence root-cause hypothesis a developer could act on immediately (e.g. "Frontend grid
cache not refreshed after invoice creation" rather than "test failed"). Also assign a severity based on
business impact: critical (data loss/security/blocks core flow), high (feature broken), medium (degraded
but workable), low (cosmetic). Respond with ONLY the JSON object, no prose."""


def _compute_confidence(state: RunState) -> tuple[float, str]:
    findings = state.get("validation_findings", [])
    step_results = state.get("step_results", [])

    if state.get("execution_error"):
        return 0.0, "errored"

    if not findings:
        return 0.0, "errored"

    met = [f for f in findings if f["outcome"] == "met"]
    not_met = [f for f in findings if f["outcome"] == "not_met"]

    failed_steps = [s for s in step_results if s["status"] == "failed"]
    step_pass_ratio = 1.0 - (len(failed_steps) / len(step_results)) if step_results else 0.0

    finding_confidences = [f["confidence"] for f in findings]
    avg_finding_confidence = sum(finding_confidences) / len(finding_confidences) if finding_confidences else 0.0
    outcome_ratio = len(met) / len(findings) if findings else 0.0

    score = round((0.5 * outcome_ratio + 0.3 * avg_finding_confidence + 0.2 * step_pass_ratio), 4)

    if not_met or failed_steps:
        final_status = "failed"
    elif score >= 0.6:
        final_status = "passed"
    else:
        final_status = "failed"

    return score, final_status


async def run_comparator_agent(state: RunState, llm: LLMProvider) -> RunState:
    confidence_score, final_status = _compute_confidence(state)

    root_cause_hypothesis: str | None = None
    severity: str | None = None

    if final_status in ("failed", "errored"):
        failed_steps = [s for s in state.get("step_results", []) if s["status"] == "failed"]
        not_met_findings = [f for f in state.get("validation_findings", []) if f["outcome"] == "not_met"]
        user_prompt = json.dumps(
            {
                "requirement": state.get("requirement_text"),
                "execution_error": state.get("execution_error"),
                "failed_steps": failed_steps,
                "not_met_findings": not_met_findings,
            }
        )
        raw = await llm.chat(
            [
                ChatMessage(role="system", content=ROOT_CAUSE_SYSTEM_PROMPT),
                ChatMessage(role="user", content=user_prompt),
            ],
            json_schema=ROOT_CAUSE_SCHEMA,
        )
        parsed = parse_json_object(raw)
        root_cause_hypothesis = parsed["root_cause_hypothesis"]
        severity = parsed["severity"]

    return {
        **state,
        "confidence_score": confidence_score,
        "final_status": final_status,
        "severity": severity,
        "root_cause_hypothesis": root_cause_hypothesis,
    }
