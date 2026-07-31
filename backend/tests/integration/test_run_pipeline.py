"""The one test that drives the run pipeline end-to-end.

Route-level run tests (test_runs.py) only check that creating a Run enqueues
a Celery task — they never execute it, by design, to keep the HTTP test
suite fast. This test proves the other half: that
app.execution.tasks._run_requirement_async actually wires
RequirementAgent -> PlannerAgent -> Executor -> ValidatorAgent ->
ComparatorAgent -> ReportAgent (app.agents.graph.build_run_graph) together
and persists a coherent result to Postgres.

The LLM is mocked (StubLLMProvider, via the autouse stub_external_services
fixture). The Executor is ALSO mocked here (FakeSuccessExecutor) — this is
an integration test for the graph/DB wiring, not for Playwright, which is
covered for real in tests/e2e/test_run_pipeline_e2e.py.
"""
from __future__ import annotations

import uuid

import httpx

from app.execution import tasks as tasks_module
from tests.support.stubs import FakeSuccessExecutor


async def test_run_pipeline_executes_and_persists_a_passing_run(
    client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID, monkeypatch
):
    monkeypatch.setattr("app.agents.executor_node.get_executor_class", lambda platform: FakeSuccessExecutor)
    monkeypatch.setattr("app.execution.tasks.publish_sync", lambda *args, **kwargs: None)

    requirement = await client.post(
        f"/api/v1/projects/{project_id}/requirements",
        json={"text": "Admin can create an invoice and it appears in the ledger."},
        headers=owner_headers,
    )
    requirement_id = requirement.json()["id"]

    run = await client.post(
        f"/api/v1/projects/{project_id}/runs", json={"requirement_id": requirement_id}, headers=owner_headers
    )
    run_id = run.json()["id"]
    assert run.json()["status"] == "queued"

    await tasks_module._run_requirement_async(uuid.UUID(run_id))

    fetched = await client.get(f"/api/v1/projects/{project_id}/runs/{run_id}", headers=owner_headers)
    assert fetched.status_code == 200, fetched.text
    body = fetched.json()

    # Deterministic given FakeSuccessExecutor (all steps pass) + StubLLMProvider's default
    # findings (one outcome "met" at confidence 0.9) — see app.agents.comparator_agent._compute_confidence.
    assert body["status"] == "passed"
    assert body["plan"] is not None and body["plan"]["steps"]
    assert body["confidence_score"] is not None
    assert body["report_markdown"] is not None
    assert body["started_at"] is not None
    assert body["finished_at"] is not None

    assert len(body["steps"]) == len(body["plan"]["steps"])
    for step in body["steps"]:
        assert step["status"] == "passed"
        assert any(e["evidence_type"] == "screenshot" for e in step["evidence"])
