"""Integration tests for app.api.routers.runs.

Celery execution itself is out of scope here (see stub_celery in conftest —
`.delay` is replaced with a MagicMock at the route level); these tests only
check the HTTP contract: enqueue-on-create, project-scoped lookups, and the
cancel state machine. The one test that actually drives the run pipeline
end-to-end lives in test_run_pipeline.py.
"""
from __future__ import annotations

import uuid

import httpx

from app.db.models.run import Run
from app.domain.enums import RunStatus


async def _create_requirement(client: httpx.AsyncClient, headers: dict, project_id: uuid.UUID, text_: str = "Do the thing") -> str:
    resp = await client.post(f"/api/v1/projects/{project_id}/requirements", json={"text": text_}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


async def test_create_run_enqueues_celery_task(
    client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID, stub_celery: dict
):
    requirement_id = await _create_requirement(client, owner_headers, project_id)

    resp = await client.post(
        f"/api/v1/projects/{project_id}/runs", json={"requirement_id": requirement_id}, headers=owner_headers
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "queued"

    # create_run() pins the Celery task_id to the run's own id via apply_async(...) so
    # POST /{run_id}/cancel can revoke that exact in-flight task later.
    stub_celery["run_requirement_task"].apply_async.assert_called_once_with(
        args=[body["id"]], task_id=body["id"]
    )


async def test_create_run_with_unknown_requirement_404s(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    resp = await client.post(
        f"/api/v1/projects/{project_id}/runs", json={"requirement_id": str(uuid.uuid4())}, headers=owner_headers
    )
    assert resp.status_code == 404


async def test_list_runs(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    requirement_id = await _create_requirement(client, owner_headers, project_id)
    create = await client.post(
        f"/api/v1/projects/{project_id}/runs", json={"requirement_id": requirement_id}, headers=owner_headers
    )
    run_id = create.json()["id"]

    resp = await client.get(f"/api/v1/projects/{project_id}/runs", headers=owner_headers)
    assert resp.status_code == 200
    assert run_id in [r["id"] for r in resp.json()]


async def test_get_run(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    requirement_id = await _create_requirement(client, owner_headers, project_id)
    create = await client.post(
        f"/api/v1/projects/{project_id}/runs", json={"requirement_id": requirement_id}, headers=owner_headers
    )
    run_id = create.json()["id"]

    resp = await client.get(f"/api/v1/projects/{project_id}/runs/{run_id}", headers=owner_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == run_id
    assert resp.json()["steps"] == []


async def test_get_run_across_project_boundary_404s(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    requirement_id = await _create_requirement(client, owner_headers, project_id)
    create = await client.post(
        f"/api/v1/projects/{project_id}/runs", json={"requirement_id": requirement_id}, headers=owner_headers
    )
    run_id = create.json()["id"]

    other_project = await client.post(
        "/api/v1/projects",
        json={"name": "Other", "platform": "web", "base_url": "https://other.example.com"},
        headers=owner_headers,
    )
    other_project_id = other_project.json()["id"]

    resp = await client.get(f"/api/v1/projects/{other_project_id}/runs/{run_id}", headers=owner_headers)
    assert resp.status_code == 404


async def test_get_unknown_run_404s(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    resp = await client.get(f"/api/v1/projects/{project_id}/runs/{uuid.uuid4()}", headers=owner_headers)
    assert resp.status_code == 404


async def test_cancel_non_terminal_run_succeeds(
    client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID, stub_celery: dict
):
    requirement_id = await _create_requirement(client, owner_headers, project_id)
    create = await client.post(
        f"/api/v1/projects/{project_id}/runs", json={"requirement_id": requirement_id}, headers=owner_headers
    )
    run_id = create.json()["id"]
    assert create.json()["status"] == "queued"

    resp = await client.post(f"/api/v1/projects/{project_id}/runs/{run_id}/cancel", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "cancelled"


async def test_cancel_terminal_run_conflicts(
    client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID, db_session
):
    requirement_id = await _create_requirement(client, owner_headers, project_id)
    create = await client.post(
        f"/api/v1/projects/{project_id}/runs", json={"requirement_id": requirement_id}, headers=owner_headers
    )
    run_id = create.json()["id"]

    # Force the run into a terminal state directly, as the run pipeline would.
    run_row = await db_session.get(Run, uuid.UUID(run_id))
    run_row.status = RunStatus.PASSED
    await db_session.commit()

    resp = await client.post(f"/api/v1/projects/{project_id}/runs/{run_id}/cancel", headers=owner_headers)
    assert resp.status_code == 409


async def test_cancel_run_across_project_boundary_404s(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    requirement_id = await _create_requirement(client, owner_headers, project_id)
    create = await client.post(
        f"/api/v1/projects/{project_id}/runs", json={"requirement_id": requirement_id}, headers=owner_headers
    )
    run_id = create.json()["id"]

    other_project = await client.post(
        "/api/v1/projects",
        json={"name": "Other", "platform": "web", "base_url": "https://other.example.com"},
        headers=owner_headers,
    )
    other_project_id = other_project.json()["id"]

    resp = await client.post(f"/api/v1/projects/{other_project_id}/runs/{run_id}/cancel", headers=owner_headers)
    assert resp.status_code == 404
