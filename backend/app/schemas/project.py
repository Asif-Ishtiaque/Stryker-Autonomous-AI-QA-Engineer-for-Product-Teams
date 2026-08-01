from __future__ import annotations

import uuid
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

from app.domain.enums import Platform, ProjectEnvironment, ProjectStatus


def _require_http_url(value: str) -> str:
    """Rejects anything that isn't a real http(s) URL.

    base_url is stored as a plain str (not pydantic's HttpUrl) because every
    consumer — the web executor's urljoin, the frontend, the DB column — wants
    a plain string, not a wrapped URL type. Without this check, Pydantic
    happily accepted literally anything (an email address made it into a real
    project's base_url in testing), and the failure only surfaced much later
    as a confusing Playwright navigation error deep inside a run.
    """
    parsed = urlparse(value.strip())
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError(f"base_url must be a full http(s) URL, e.g. https://staging.myapp.com — got {value!r}")
    return value.strip()


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    platform: Platform
    environment: ProjectEnvironment = ProjectEnvironment.STAGING
    base_url: str
    tags: list[str] = Field(default_factory=list)

    _validate_base_url = field_validator("base_url")(_require_http_url)


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    environment: ProjectEnvironment | None = None
    base_url: str | None = None
    tags: list[str] | None = None
    status: ProjectStatus | None = None

    @field_validator("base_url")
    @classmethod
    def _validate_base_url(cls, value: str | None) -> str | None:
        return _require_http_url(value) if value is not None else value


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    platform: Platform
    environment: ProjectEnvironment
    base_url: str
    tags: list[str]
    status: ProjectStatus

    model_config = {"from_attributes": True}


class ProjectStats(BaseModel):
    """Summary numbers shown on the dashboard/project overview card."""

    requirement_count: int
    run_count: int
    pass_rate: float
    average_duration_ms: float | None
    open_bugs: int
    average_confidence: float | None
