"""ComparatorAgent — reduces validation findings + execution outcome into a
single confidence score, severity, final status, and (on failure) a
structured root-cause analysis a developer can act on immediately.

The confidence score is computed deterministically from the findings rather
than asked of the LLM directly, so it's reproducible and auditable; the LLM
is only used for the qualitative root-cause analysis when something failed,
and only from evidence actually captured during the run (console errors,
network failures with status codes, validation findings) — never invented.
"""
from __future__ import annotations

import json
from typing import Any

from app.agents.state import ExecutedStepResult, RunState
from app.llm.base import ChatMessage, LLMProvider, parse_json_object

ROOT_CAUSE_SCHEMA = {
    "type": "object",
    "properties": {
        "observed_behavior": {"type": "string"},
        "expected_behavior": {"type": "string"},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "root_cause": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "suggested_fix": {"type": "string"},
        "affected_component": {
            "type": "string",
            "enum": ["frontend", "backend", "api", "database", "infra", "test_data", "third_party", "unknown"],
        },
        "severity": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
        "likely_owner": {"type": "string"},
    },
    "required": [
        "observed_behavior",
        "expected_behavior",
        "evidence",
        "root_cause",
        "confidence",
        "suggested_fix",
        "affected_component",
        "severity",
        "likely_owner",
    ],
}

ROOT_CAUSE_SYSTEM_PROMPT = """You are a senior engineer triaging a failed QA run. You are given the
requirement, the step(s) that failed or the business outcome that was not met, and the evidence
gathered during execution (console errors, network failures with HTTP status codes and response
bodies, validation findings). Produce a structured root-cause analysis:

- observed_behavior: what actually happened, in plain language, citing specifics (e.g. "clicking
  'Create Invoice' returned no visible error but the invoice list stayed empty").
- expected_behavior: what should have happened per the requirement.
- evidence: 2-5 short strings, each citing a concrete signal from the input (a console error message,
  an HTTP status code and URL, a specific validation finding). Never invent evidence that isn't present
  in the input — if there is genuinely nothing concrete, say so as one of the evidence entries.
- root_cause: a one-to-three sentence hypothesis a developer could act on immediately (e.g. "Frontend
  grid cache not refreshed after invoice creation" rather than "test failed"). If the evidence is
  inconclusive, hypothesize the most likely explanation and lower your confidence — never output "test
  failed" alone.
- confidence: 0-1, how confident you are in THIS specific root cause given the evidence available.
- suggested_fix: one concrete, actionable suggestion for the developer who owns this.
- affected_component: one of frontend, backend, api, database, infra, test_data, third_party, unknown.
- severity: business impact — critical (data loss/security/blocks core flow), high (feature broken),
  medium (degraded but workable), low (cosmetic).
- likely_owner: the team most likely responsible (e.g. "frontend engineering", "backend/API team",
  "infra/DevOps", "QA/test data") — infer from affected_component, not a guess at a person's name.

Respond with ONLY the JSON object, no prose."""


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

    # Defensive clamp: the ValidatorAgent's JSON schema asks for confidence in [0, 1], but a
    # smaller local model doesn't reliably respect that (observed returning categorical-looking
    # values like 0/1/2, or worse) — trusting it unclamped let a single bad finding blow the
    # final score past 1.0 (seen: 23.8857, i.e. "2389% confidence" in the UI). Every value this
    # function reads from the LLM is clamped at the point of use, not just at the schema layer.
    finding_confidences = [max(0.0, min(1.0, f["confidence"])) for f in findings]
    avg_finding_confidence = sum(finding_confidences) / len(finding_confidences) if finding_confidences else 0.0
    outcome_ratio = len(met) / len(findings) if findings else 0.0

    score = round(max(0.0, min(1.0, 0.5 * outcome_ratio + 0.3 * avg_finding_confidence + 0.2 * step_pass_ratio)), 4)

    if not_met or failed_steps:
        final_status = "failed"
    elif score >= 0.6:
        final_status = "passed"
    else:
        final_status = "failed"

    return score, final_status


def _summarize_failed_step(step: ExecutedStepResult, plan_by_seq: dict[int, str]) -> dict[str, Any]:
    """Pulls out just the console errors and 4xx/5xx network failures captured
    during this step, so the LLM sees a short, grounded signal instead of the
    full evidence_refs list (which also carries screenshot/DOM storage keys
    that are useless to it and would only burn context)."""
    console_errors: list[dict[str, Any]] = []
    network_failures: list[dict[str, Any]] = []
    for ref in step.get("evidence_refs", []):
        entries = (ref.get("inline_data") or {}).get("entries", [])
        if ref.get("evidence_type") == "console_log":
            console_errors.extend(e for e in entries if e.get("type") == "error")
        elif ref.get("evidence_type") == "network_log":
            network_failures.extend(e for e in entries if isinstance(e.get("status"), int) and e["status"] >= 400)

    return {
        "sequence": step["sequence"],
        "step_name": plan_by_seq.get(step["sequence"]),
        "error_message": step.get("error_message"),
        "console_errors": console_errors,
        "network_failures": network_failures,
    }


async def run_comparator_agent(state: RunState, llm: LLMProvider) -> RunState:
    confidence_score, final_status = _compute_confidence(state)

    root_cause_analysis: dict[str, Any] | None = None
    root_cause_hypothesis: str | None = None
    severity: str | None = None

    if final_status in ("failed", "errored"):
        plan_by_seq = {p["sequence"]: p["name"] for p in state.get("plan", [])}
        failed_steps = [
            _summarize_failed_step(s, plan_by_seq) for s in state.get("step_results", []) if s["status"] == "failed"
        ]
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
        parsed["confidence"] = max(0.0, min(1.0, parsed.get("confidence", 0.0)))
        root_cause_analysis = parsed
        root_cause_hypothesis = parsed["root_cause"]
        severity = parsed["severity"]

    return {
        **state,
        "confidence_score": confidence_score,
        "final_status": final_status,
        "severity": severity,
        "root_cause_hypothesis": root_cause_hypothesis,
        "root_cause_analysis": root_cause_analysis,
    }
