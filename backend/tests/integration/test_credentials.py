"""Integration tests for app.api.routers.credentials.

The whole point of CredentialProfile is that plaintext secrets never leave
the encryption boundary — these tests assert that as directly as possible:
the API response for a credential must contain no plaintext secret value,
and no key named after a plaintext field at all (only the has_* booleans).
"""
from __future__ import annotations

import uuid

import httpx

_PLAINTEXT_KEYS = {"username", "password", "api_token", "bearer_token", "cookies", "headers", "env_vars"}


async def test_create_credential_with_all_fields(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    resp = await client.post(
        f"/api/v1/projects/{project_id}/credentials",
        json={
            "label": "Admin",
            "username": "admin@example.com",
            "password": "sup3r-secret",
            "api_token": "tok_abc123",
            "bearer_token": "bearer_xyz",
            "cookies": {"session": "abc"},
            "headers": {"X-Api-Key": "k"},
            "env_vars": {"STAGE": "qa"},
        },
        headers=owner_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["label"] == "Admin"
    assert body["has_username"] is True
    assert body["has_password"] is True
    assert body["has_api_token"] is True
    assert body["has_bearer_token"] is True
    assert body["has_cookies"] is True
    assert body["has_headers"] is True
    assert not (_PLAINTEXT_KEYS & body.keys())


async def test_create_credential_with_only_some_fields(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    resp = await client.post(
        f"/api/v1/projects/{project_id}/credentials",
        json={"label": "Read-only viewer", "api_token": "tok_only"},
        headers=owner_headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["has_api_token"] is True
    assert body["has_username"] is False
    assert body["has_password"] is False
    assert body["has_bearer_token"] is False
    assert body["has_cookies"] is False
    assert body["has_headers"] is False


async def test_list_credentials_never_leaks_plaintext(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    await client.post(
        f"/api/v1/projects/{project_id}/credentials",
        json={"label": "Admin", "username": "u", "password": "p"},
        headers=owner_headers,
    )
    resp = await client.get(f"/api/v1/projects/{project_id}/credentials", headers=owner_headers)
    assert resp.status_code == 200
    profiles = resp.json()
    assert len(profiles) == 1
    for profile in profiles:
        assert not (_PLAINTEXT_KEYS & profile.keys())
        assert profile["has_username"] is True
        assert profile["has_password"] is True


async def test_delete_credential(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    create = await client.post(
        f"/api/v1/projects/{project_id}/credentials", json={"label": "Temp"}, headers=owner_headers
    )
    credential_id = create.json()["id"]

    resp = await client.delete(f"/api/v1/projects/{project_id}/credentials/{credential_id}", headers=owner_headers)
    assert resp.status_code == 204

    listing = await client.get(f"/api/v1/projects/{project_id}/credentials", headers=owner_headers)
    assert listing.json() == []


async def test_delete_credential_from_wrong_project_404s(
    client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID
):
    create = await client.post(
        f"/api/v1/projects/{project_id}/credentials", json={"label": "Temp"}, headers=owner_headers
    )
    credential_id = create.json()["id"]

    other_project = await client.post(
        "/api/v1/projects",
        json={"name": "Other", "platform": "web", "base_url": "https://other.example.com"},
        headers=owner_headers,
    )
    other_project_id = other_project.json()["id"]

    resp = await client.delete(
        f"/api/v1/projects/{other_project_id}/credentials/{credential_id}", headers=owner_headers
    )
    assert resp.status_code == 404


async def test_delete_unknown_credential_404s(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    resp = await client.delete(
        f"/api/v1/projects/{project_id}/credentials/{uuid.uuid4()}", headers=owner_headers
    )
    assert resp.status_code == 404
