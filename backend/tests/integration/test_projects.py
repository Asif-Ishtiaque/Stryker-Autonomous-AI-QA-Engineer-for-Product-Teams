"""Integration tests for app.api.routers.projects."""
from __future__ import annotations

import uuid

import httpx


async def test_create_project(client: httpx.AsyncClient, owner_headers: dict):
    resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "Checkout",
            "description": "Checkout flows",
            "platform": "web",
            "environment": "staging",
            "base_url": "https://shop.example.com",
            "tags": ["checkout", "payments"],
        },
        headers=owner_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Checkout"
    assert body["tags"] == ["checkout", "payments"]
    assert body["status"] == "active"
    assert body["environment"] == "staging"


async def test_list_projects(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    resp = await client.get("/api/v1/projects", headers=owner_headers)
    assert resp.status_code == 200
    ids = [p["id"] for p in resp.json()]
    assert str(project_id) in ids


async def test_get_project(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    resp = await client.get(f"/api/v1/projects/{project_id}", headers=owner_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == str(project_id)


async def test_get_unknown_project_404s(client: httpx.AsyncClient, owner_headers: dict):
    resp = await client.get(f"/api/v1/projects/{uuid.uuid4()}", headers=owner_headers)
    assert resp.status_code == 404


async def test_patch_project_updates_only_provided_fields(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    resp = await client.patch(
        f"/api/v1/projects/{project_id}",
        json={"description": "Updated description", "status": "paused"},
        headers=owner_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["description"] == "Updated description"
    assert body["status"] == "paused"
    assert body["name"] == "Invoicing"  # untouched


async def test_patch_unknown_project_404s(client: httpx.AsyncClient, owner_headers: dict):
    resp = await client.patch(f"/api/v1/projects/{uuid.uuid4()}", json={"name": "x"}, headers=owner_headers)
    assert resp.status_code == 404


async def test_delete_project(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    resp = await client.delete(f"/api/v1/projects/{project_id}", headers=owner_headers)
    assert resp.status_code == 204

    follow_up = await client.get(f"/api/v1/projects/{project_id}", headers=owner_headers)
    assert follow_up.status_code == 404


async def test_delete_unknown_project_404s(client: httpx.AsyncClient, owner_headers: dict):
    resp = await client.delete(f"/api/v1/projects/{uuid.uuid4()}", headers=owner_headers)
    assert resp.status_code == 404


async def test_stats_are_zero_for_a_project_with_no_runs(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    resp = await client.get(f"/api/v1/projects/{project_id}/stats", headers=owner_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body == {
        "requirement_count": 0,
        "run_count": 0,
        "pass_rate": 0.0,
        "average_duration_ms": None,
        "open_bugs": 0,
        "average_confidence": None,
    }
