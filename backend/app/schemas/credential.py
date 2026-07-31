from __future__ import annotations

import uuid

from pydantic import BaseModel


class CredentialCreate(BaseModel):
    label: str
    username: str | None = None
    password: str | None = None
    api_token: str | None = None
    bearer_token: str | None = None
    cookies: dict[str, str] | None = None
    headers: dict[str, str] | None = None
    env_vars: dict[str, str] | None = None


class CredentialOut(BaseModel):
    """Never includes decrypted secret values — only metadata, by design."""

    id: uuid.UUID
    project_id: uuid.UUID
    label: str
    has_username: bool
    has_password: bool
    has_api_token: bool
    has_bearer_token: bool
    has_cookies: bool
    has_headers: bool
