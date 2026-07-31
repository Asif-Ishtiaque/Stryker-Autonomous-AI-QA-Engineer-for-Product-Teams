"""The one real end-to-end test: app.agents.graph.build_run_graph driven all the way through
against a REAL Chromium browser (via the real WebExecutor / SelfHealingLocator / evidence capture
code paths) navigating a real local HTML page (tests/e2e/fixtures/demo_app.html).

Only the LLM is mocked (StubLLMProvider, hand-configured with a plan that matches demo_app.html's
actual elements) — everything else in the pipeline is real:
  - Playwright launches a real headless Chromium and drives a real page.
  - The self-healing locator engine resolves every target against the live accessibility tree.
  - Evidence capture takes real screenshots/DOM snapshots of that real page.

The only thing NOT real is where the resulting bytes get stored afterward (an in-memory dict
standing in for MinIO, per the same "mock infra at the network edge" rule used everywhere else in
this test suite) — that's storage, not the thing under test.
"""
from __future__ import annotations

from app.agents.graph import build_run_graph
from tests.support.stubs import StubLLMProvider

REQUIREMENT_RESPONSE = {
    "understood_intent": "A user can log in and the app confirms it, and a new invoice line item can be added.",
    "expected_outcomes": [
        "A welcome banner is shown after logging in",
        "A new invoice line item appears in the invoice table",
    ],
    "inferred_validations": [],
    "identified_risks": ["Login silently failing without feedback"],
    "predicted_edge_cases": ["Empty username"],
    "confidence": 0.9,
}

# Hand-written to match tests/e2e/fixtures/demo_app.html's real elements exactly, so every
# fill/click resolves via the locator engine's role_and_name strategy (see
# app.agents.executors.web.locator_engine.SelfHealingLocator) — never the LLM semantic fallback.
PLAN_STEPS = [
    {
        "sequence": 1,
        "name": "Navigate to the demo app",
        "action_type": "navigate",
        "parameters": {"url": "demo_app.html"},
        "expected_outcome": "The login form is visible",
    },
    {
        "sequence": 2,
        "name": "Fill username",
        "action_type": "fill",
        "parameters": {"description": "Username field", "role": "textbox", "text_hint": "Username", "value": "demo_user"},
        "expected_outcome": "Username is entered",
    },
    {
        "sequence": 3,
        "name": "Fill password",
        "action_type": "fill",
        "parameters": {"description": "Password field", "role": "textbox", "text_hint": "Password", "value": "Sup3rSecret!"},
        "expected_outcome": "Password is entered",
    },
    {
        "sequence": 4,
        "name": "Submit login form",
        "action_type": "click",
        "parameters": {"description": "Log In button", "role": "button", "text_hint": "Log In"},
        "expected_outcome": "The form is submitted",
    },
    {
        "sequence": 5,
        "name": "Assert welcome banner is shown",
        "action_type": "assert_text",
        "parameters": {"text": "Welcome"},
        "expected_outcome": "A welcome banner is shown after logging in",
    },
    {
        "sequence": 6,
        "name": "Add an invoice row",
        "action_type": "click",
        "parameters": {"description": "Add Invoice Row button", "role": "button", "text_hint": "Add Invoice Row"},
        "expected_outcome": "A new invoice line item is added",
    },
    {
        "sequence": 7,
        "name": "Assert the new invoice row appears",
        "action_type": "assert_text",
        "parameters": {"text": "New line item"},
        "expected_outcome": "A new invoice line item appears in the invoice table",
    },
]

FINDINGS = [
    {
        "checked": "A welcome banner is shown after logging in",
        "outcome": "met",
        "evidence": "The #welcome-banner element became visible with text 'Welcome, demo_user!'",
        "confidence": 0.95,
    },
    {
        "checked": "A new invoice line item appears in the invoice table",
        "outcome": "met",
        "evidence": "A new row containing 'New line item' was appended to the invoice table",
        "confidence": 0.9,
    },
]


async def test_full_pipeline_runs_against_a_real_browser_with_self_healing_locators(
    demo_app_base_url: str, small_browser_pool, monkeypatch
):
    from tests.support.stubs import InMemoryEvidenceStorage

    storage = InMemoryEvidenceStorage()
    monkeypatch.setattr("app.evidence.capture.get_evidence_storage", lambda: storage)

    llm = StubLLMProvider(
        requirement_response=REQUIREMENT_RESPONSE,
        plan_steps=PLAN_STEPS,
        findings=FINDINGS,
    )

    events: list[dict] = []

    async def on_event(event: dict) -> None:
        events.append(event)

    initial_state = {
        "run_id": "e2e-test-run",
        "project_id": "e2e-test-project",
        "platform": "web",
        "base_url": demo_app_base_url,
        "requirement_text": "A user can log in and add an invoice line item.",
        "knowledge_context": [],
        "credential": None,
        "plan_retry_count": 0,
    }

    graph = build_run_graph(llm, on_event)
    final_state = await graph.ainvoke(initial_state, config={"recursion_limit": 50})

    # 1. The run reached a terminal status.
    assert final_state.get("final_status") == "passed", final_state.get("execution_error")

    # 2. Every step actually executed against the real page and passed.
    step_results = final_state["step_results"]
    assert len(step_results) == len(PLAN_STEPS)
    assert all(r["status"] == "passed" for r in step_results), step_results

    # 3. At least one real screenshot was captured (and actually "stored").
    screenshot_refs = [
        ref
        for result in step_results
        for ref in result["evidence_refs"]
        if ref["evidence_type"] == "screenshot"
    ]
    assert screenshot_refs, "expected at least one screenshot evidence entry"
    for ref in screenshot_refs:
        assert ref["storage_key"] in storage.objects
        assert len(storage.objects[ref["storage_key"]]) > 0  # real, non-empty PNG bytes

    # 4. The locator engine resolved every target by role/text — never fell through to the LLM
    # semantic-disambiguation fallback (see SelfHealingLocator._by_llm_semantic_match).
    assert llm.semantic_disambiguation_calls == 0

    # Sanity: the graph really drove the LLM through every stage of the pipeline (not just the
    # locator's fallback path, which we just asserted never fired).
    assert len(llm.calls) >= 4  # requirement, planner, validator, report (comparator skipped: passed)
