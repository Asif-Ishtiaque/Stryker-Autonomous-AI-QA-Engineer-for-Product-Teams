"""PlannerAgent — turns the RequirementAgent's structured understanding into
an ordered, executable plan of PlannedSteps. The plan is platform-agnostic
in shape (action_type + parameters) so any registered Executor can run it;
only the *content* of parameters (e.g. `description` hints) needs to make
sense for the target platform, which the prompt is told explicitly.

Never emits a CSS/XPath selector — steps describe elements the way a human
would ("the Create Invoice button"), and self-healing resolution happens at
execution time (see app.agents.executors.web.locator_engine).
"""
from __future__ import annotations

import json

from app.agents.state import RunState
from app.llm.base import ChatMessage, LLMProvider

SCHEMA = {
    "type": "object",
    "properties": {
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sequence": {"type": "integer"},
                    "name": {"type": "string"},
                    "action_type": {
                        "type": "string",
                        "enum": [
                            "navigate",
                            "login",
                            "click",
                            "fill",
                            "select",
                            "check",
                            "uncheck",
                            "hover",
                            "wait",
                            "assert_text",
                            "assert_business_outcome",
                            "api_call",
                        ],
                    },
                    "parameters": {"type": "object"},
                    "expected_outcome": {"type": "string"},
                },
                "required": ["sequence", "name", "action_type", "parameters", "expected_outcome"],
            },
        }
    },
    "required": ["steps"],
}

SYSTEM_PROMPT = """You are a senior QA automation engineer writing an execution plan — NOT code.
You never reference CSS selectors, XPath, or DOM structure. Instead, describe the target of any
UI action the way a human tester would: "the Create Invoice button", "the customer email field".

Rules:
- Always start with a "login" step if a credential is available and the requirement implies an
  authenticated action, using action_type "login" with parameters {} (the executor knows how to log in).
- Use action_type "navigate" with parameters {"url": "/path"} for page changes.
- Use "click"/"fill"/"select"/"check"/"uncheck"/"hover" with parameters
  {"description": "...", "role": "button|textbox|link|checkbox|combobox", "text_hint": "...", "test_id_hint": "..."}.
  Only "description" is required; fill the others when you can reasonably guess them.
- Use "assert_text" with parameters {"text": "..."} for simple visible-text checks.
- Use "assert_business_outcome" with parameters {} whenever a step corresponds to one of the
  requirement's expected_outcomes or inferred_validations — set expected_outcome to the exact
  outcome text so the ValidatorAgent knows what it's checking.
- For REST API platforms, use action_type "api_call" with parameters
  {"method": "GET|POST|PUT|DELETE|PATCH", "path": "...", "body": {...}, "headers": {...}}.
- Number steps sequentially starting at 1. Keep the plan as short as possible while still covering
  every expected_outcome and inferred_validation from the requirement analysis.
Respond with ONLY the JSON object, no prose."""


async def run_planner_agent(state: RunState, llm: LLMProvider) -> RunState:
    user_prompt = json.dumps(
        {
            "platform": state["platform"],
            "base_url": state["base_url"],
            "understood_intent": state.get("understood_intent"),
            "expected_outcomes": state.get("expected_outcomes", []),
            "inferred_validations": state.get("inferred_validations", []),
            "has_credential": state.get("credential") is not None,
            "previous_execution_error": state.get("execution_error"),
        }
    )
    raw = await llm.chat(
        [ChatMessage(role="system", content=SYSTEM_PROMPT), ChatMessage(role="user", content=user_prompt)],
        json_schema=SCHEMA,
    )
    parsed = json.loads(raw)
    steps = sorted(parsed["steps"], key=lambda s: s["sequence"])

    return {
        **state,
        "plan": steps,
        "plan_retry_count": state.get("plan_retry_count", 0),
    }
