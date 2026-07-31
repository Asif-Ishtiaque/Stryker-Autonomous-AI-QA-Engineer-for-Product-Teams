"""Integration tests for app.api.routers.requirements.

analyze_requirement drives the real RequirementAgent against a stubbed
LLMProvider (see tests/support/stubs.StubLLMProvider) whose canned response
is DEFAULT_REQUIREMENT_RESPONSE — the assertions below check that exact
shape flows through unchanged and gets persisted onto the row.
"""
from __future__ import annotations

import uuid

import httpx

from tests.support.stubs import DEFAULT_REQUIREMENT_RESPONSE


async def test_create_requirement(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    resp = await client.post(
        f"/api/v1/projects/{project_id}/requirements",
        json={"text": "Admin can create an invoice and it appears in the customer's ledger."},
        headers=owner_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["project_id"] == str(project_id)
    assert body["ai_analysis"] is None


async def test_list_requirements(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    await client.post(
        f"/api/v1/projects/{project_id}/requirements", json={"text": "Req A"}, headers=owner_headers
    )
    await client.post(
        f"/api/v1/projects/{project_id}/requirements", json={"text": "Req B"}, headers=owner_headers
    )
    resp = await client.get(f"/api/v1/projects/{project_id}/requirements", headers=owner_headers)
    assert resp.status_code == 200
    assert {r["text"] for r in resp.json()} == {"Req A", "Req B"}


async def test_get_requirement(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    create = await client.post(
        f"/api/v1/projects/{project_id}/requirements", json={"text": "Req"}, headers=owner_headers
    )
    requirement_id = create.json()["id"]

    resp = await client.get(
        f"/api/v1/projects/{project_id}/requirements/{requirement_id}", headers=owner_headers
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == requirement_id


async def test_get_requirement_from_wrong_project_404s(
    client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID
):
    create = await client.post(
        f"/api/v1/projects/{project_id}/requirements", json={"text": "Req"}, headers=owner_headers
    )
    requirement_id = create.json()["id"]

    resp = await client.get(
        f"/api/v1/projects/{uuid.uuid4()}/requirements/{requirement_id}", headers=owner_headers
    )
    assert resp.status_code == 404


async def test_analyze_requirement_persists_ai_analysis(
    client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID
):
    create = await client.post(
        f"/api/v1/projects/{project_id}/requirements",
        json={"text": "Admin can create an invoice."},
        headers=owner_headers,
    )
    requirement_id = create.json()["id"]

    resp = await client.post(
        f"/api/v1/projects/{project_id}/requirements/{requirement_id}/analyze", headers=owner_headers
    )
    assert resp.status_code == 200, resp.text
    analysis = resp.json()
    assert analysis["understood_intent"] == DEFAULT_REQUIREMENT_RESPONSE["understood_intent"]
    assert analysis["expected_outcomes"] == DEFAULT_REQUIREMENT_RESPONSE["expected_outcomes"]
    assert analysis["confidence"] == DEFAULT_REQUIREMENT_RESPONSE["confidence"]

    # ai_analysis must actually be persisted on the row, not just returned once.
    fetched = await client.get(
        f"/api/v1/projects/{project_id}/requirements/{requirement_id}", headers=owner_headers
    )
    assert fetched.json()["ai_analysis"]["understood_intent"] == DEFAULT_REQUIREMENT_RESPONSE["understood_intent"]


async def test_analyze_unknown_requirement_404s(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    resp = await client.post(
        f"/api/v1/projects/{project_id}/requirements/{uuid.uuid4()}/analyze", headers=owner_headers
    )
    assert resp.status_code == 404
