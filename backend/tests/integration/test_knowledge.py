"""Integration tests for app.api.routers.knowledge."""
from __future__ import annotations

import uuid

import httpx


async def test_upload_with_unsupported_extension_400s(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    files = {"file": ("malware.exe", b"binary-garbage", "application/octet-stream")}
    resp = await client.post(f"/api/v1/projects/{project_id}/knowledge/upload", files=files, headers=owner_headers)
    assert resp.status_code == 400


async def test_upload_txt_file_succeeds_and_enqueues_ingestion(
    client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID, stub_celery: dict
):
    files = {"file": ("notes.txt", b"Admins can create invoices.", "text/plain")}
    resp = await client.post(f"/api/v1/projects/{project_id}/knowledge/upload", files=files, headers=owner_headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["filename"] == "notes.txt"
    assert body["source_type"] == "txt"
    assert body["status"] == "pending"

    stub_celery["ingest_knowledge_source_task"].delay.assert_called_once_with(body["id"])


async def test_list_knowledge_sources(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    files = {"file": ("notes.txt", b"some text", "text/plain")}
    await client.post(f"/api/v1/projects/{project_id}/knowledge/upload", files=files, headers=owner_headers)

    resp = await client.get(f"/api/v1/projects/{project_id}/knowledge", headers=owner_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["filename"] == "notes.txt"


async def test_delete_knowledge_source(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    files = {"file": ("notes.txt", b"some text", "text/plain")}
    upload = await client.post(f"/api/v1/projects/{project_id}/knowledge/upload", files=files, headers=owner_headers)
    source_id = upload.json()["id"]

    resp = await client.delete(f"/api/v1/projects/{project_id}/knowledge/{source_id}", headers=owner_headers)
    assert resp.status_code == 204

    listing = await client.get(f"/api/v1/projects/{project_id}/knowledge", headers=owner_headers)
    assert listing.json() == []


async def test_delete_knowledge_source_from_wrong_project_404s(
    client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID
):
    files = {"file": ("notes.txt", b"some text", "text/plain")}
    upload = await client.post(f"/api/v1/projects/{project_id}/knowledge/upload", files=files, headers=owner_headers)
    source_id = upload.json()["id"]

    other_project = await client.post(
        "/api/v1/projects",
        json={"name": "Other", "platform": "web", "base_url": "https://other.example.com"},
        headers=owner_headers,
    )
    other_project_id = other_project.json()["id"]

    resp = await client.delete(f"/api/v1/projects/{other_project_id}/knowledge/{source_id}", headers=owner_headers)
    assert resp.status_code == 404


async def test_delete_unknown_knowledge_source_404s(client: httpx.AsyncClient, owner_headers: dict, project_id: uuid.UUID):
    resp = await client.delete(f"/api/v1/projects/{project_id}/knowledge/{uuid.uuid4()}", headers=owner_headers)
    assert resp.status_code == 404
