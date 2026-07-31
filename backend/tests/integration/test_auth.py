"""Integration tests for app.api.routers.auth against a real Postgres DB."""
from __future__ import annotations

import datetime as dt

import httpx
import jwt
import pytest

from app.core.config import get_settings


async def _register(client: httpx.AsyncClient, email: str, password: str = "s3cret-pass") -> httpx.Response:
    return await client.post("/api/v1/auth/register", json={"email": email, "name": "A User", "password": password})


async def test_first_registered_user_becomes_owner(client: httpx.AsyncClient):
    resp = await _register(client, "first@example.com")
    assert resp.status_code == 201, resp.text
    assert resp.json()["role"] == "owner"


async def test_second_registered_user_becomes_member(client: httpx.AsyncClient):
    first = await _register(client, "first@example.com")
    second = await _register(client, "second@example.com")
    assert first.json()["role"] == "owner"
    assert second.json()["role"] == "member"


async def test_registering_duplicate_email_conflicts(client: httpx.AsyncClient):
    await _register(client, "dupe@example.com")
    resp = await _register(client, "dupe@example.com")
    assert resp.status_code == 409


async def test_login_success_returns_tokens(client: httpx.AsyncClient):
    await _register(client, "login-ok@example.com", password="correct-password")
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "login-ok@example.com", "password": "correct-password"}
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_with_wrong_password_fails(client: httpx.AsyncClient):
    await _register(client, "login-bad@example.com", password="correct-password")
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "login-bad@example.com", "password": "wrong-password"}
    )
    assert resp.status_code == 401


async def test_login_with_unknown_email_fails(client: httpx.AsyncClient):
    resp = await client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.com", "password": "whatever"}
    )
    assert resp.status_code == 401


async def test_me_requires_a_valid_token(client: httpx.AsyncClient):
    await _register(client, "me@example.com", password="pw-for-me")
    login = await client.post("/api/v1/auth/login", json={"email": "me@example.com", "password": "pw-for-me"})
    token = login.json()["access_token"]

    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == "me@example.com"


async def test_me_without_a_token_is_unauthorized(client: httpx.AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


async def test_me_with_garbage_token_is_unauthorized(client: httpx.AsyncClient):
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401


async def test_me_with_expired_token_is_unauthorized(client: httpx.AsyncClient):
    await _register(client, "expired@example.com", password="pw-expired")
    settings = get_settings()
    now = dt.datetime.now(dt.timezone.utc)
    expired_token = jwt.encode(
        {
            "sub": "00000000-0000-0000-0000-000000000000",
            "role": "member",
            "type": "access",
            "iat": now - dt.timedelta(hours=2),
            "exp": now - dt.timedelta(hours=1),
        },
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401
