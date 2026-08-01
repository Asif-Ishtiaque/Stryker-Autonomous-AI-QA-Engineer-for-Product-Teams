"""ValidatorAgent — checks BUSINESS OUTCOMES, not element existence.

For every expected_outcome / inferred_validation from the RequirementAgent,
this agent looks at what the executor actually observed (step results +
evidence: DOM snapshots, API responses, accessible-name text) and judges
whether the outcome was met, not met, or inconclusive — with a confidence
per finding. "The button was clicked" is not a pass; "the invoice appeared
in the grid AND the balance updated" is.
"""
from __future__ import annotations

import json

from app.agents.state import RunState
from app.llm.base import ChatMessage, LLMProvider, parse_json_object

SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "checked": {"type": "string"},
                    "outcome": {"type": "string", "enum": ["met", "not_met", "inconclusive"]},
                    "evidence": {"type": "string"},
                    "confidence": {"type": "number"},
                },
                "required": ["checked", "outcome", "evidence", "confidence"],
            },
        }
    },
    "required": ["findings"],
}

SYSTEM_PROMPT = """You are validating whether a business requirement was actually satisfied — not
whether the automation clicked the right buttons. You will be given the requirement's expected
outcomes and inferred validations, plus what the executor observed at each step (DOM text content,
API response bodies, assertion results, error messages).

For EACH expected outcome and inferred validation, decide:
- "met": there is direct evidence in the observations that this outcome occurred
- "not_met": there is direct evidence it did NOT occur (error shown, data unchanged, wrong value)
- "inconclusive": the observations don't contain enough information to judge either way

Never mark something "met" just because a step succeeded mechanically (e.g. a click didn't error) —
only mark it "met" if the observed page/API content actually demonstrates the business outcome.
Cite the specific evidence string you're relying on for every finding.
Respond with ONLY the JSON object, no prose."""


async def run_validator_agent(state: RunState, llm: LLMProvider) -> RunState:
    checks = [*state.get("expected_outcomes", []), *state.get("inferred_validations", [])]
    observations = [
        {
            "sequence": r["sequence"],
            "status": r["status"],
            "result": r["result"],
            "error_message": r["error_message"],
        }
        for r in state.get("step_results", [])
    ]

    user_prompt = json.dumps({"checks": checks, "observations": observations})
    raw = await llm.chat(
        [ChatMessage(role="system", content=SYSTEM_PROMPT), ChatMessage(role="user", content=user_prompt)],
        json_schema=SCHEMA,
    )
    parsed = parse_json_object(raw)

    return {**state, "validation_findings": parsed["findings"]}
