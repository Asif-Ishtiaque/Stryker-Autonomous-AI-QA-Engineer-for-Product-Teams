"""RequirementAgent — turns a plain-English requirement into a structured
understanding: intent, expected outcomes, validations the user didn't
explicitly ask for but clearly implied, business risks, and edge cases.

This is the step that makes Stryker feel like a QA engineer instead of a
script recorder: "Verify Admin can create an invoice" implies checking the
invoice appears in the list, the customer balance updates, and an audit log
is written — even though the user only typed one sentence.
"""
from __future__ import annotations

from app.agents.state import RunState
from app.llm.base import ChatMessage, LLMProvider, parse_json_object

SCHEMA = {
    "type": "object",
    "properties": {
        "understood_intent": {"type": "string"},
        "expected_outcomes": {"type": "array", "items": {"type": "string"}},
        "inferred_validations": {"type": "array", "items": {"type": "string"}},
        "identified_risks": {"type": "array", "items": {"type": "string"}},
        "predicted_edge_cases": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "number"},
    },
    "required": [
        "understood_intent",
        "expected_outcomes",
        "inferred_validations",
        "identified_risks",
        "predicted_edge_cases",
        "confidence",
    ],
}

SYSTEM_PROMPT = """You are a senior QA engineer reading a business requirement before testing it.
Given the requirement and any supporting documentation context, produce:
- understood_intent: a one-sentence restatement of what must be true after the action succeeds
- expected_outcomes: concrete, observable outcomes (UI, data, notifications) — not implementation detail
- inferred_validations: checks the requirement implies but didn't state explicitly (e.g. audit logs,
  balance updates, notifications, permission boundaries)
- identified_risks: business risks if this requirement silently breaks in production
- predicted_edge_cases: edge cases worth testing later (empty states, permission boundaries, concurrency)
- confidence: 0-1, how confident you are that you understood the requirement correctly given the
  available context. Lower it if the requirement is ambiguous or the documentation doesn't cover it.
Respond with ONLY the JSON object, no prose."""


async def run_requirement_agent(state: RunState, llm: LLMProvider) -> RunState:
    context_block = "\n".join(f"- {c}" for c in state.get("knowledge_context", [])) or "(no supporting documentation provided)"
    user_prompt = (
        f"Requirement:\n{state['requirement_text']}\n\n"
        f"Platform: {state['platform']}\n\n"
        f"Supporting documentation context:\n{context_block}"
    )
    raw = await llm.chat(
        [ChatMessage(role="system", content=SYSTEM_PROMPT), ChatMessage(role="user", content=user_prompt)],
        json_schema=SCHEMA,
    )
    parsed = parse_json_object(raw)

    return {
        **state,
        "understood_intent": parsed["understood_intent"],
        "expected_outcomes": parsed["expected_outcomes"],
        "inferred_validations": parsed["inferred_validations"],
        "identified_risks": parsed["identified_risks"],
        "predicted_edge_cases": parsed["predicted_edge_cases"],
        "requirement_confidence": float(parsed["confidence"]),
    }
