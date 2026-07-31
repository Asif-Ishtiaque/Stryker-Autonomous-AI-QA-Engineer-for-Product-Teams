from __future__ import annotations

import uuid

from pydantic import BaseModel, Field

from app.domain.enums import Platform, ProjectEnvironment, ProjectStatus


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    platform: Platform
    environment: ProjectEnvironment = ProjectEnvironment.STAGING
    base_url: str
    tags: list[str] = Field(default_factory=list)


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    environment: ProjectEnvironment | None = None
    base_url: str | None = None
    tags: list[str] | None = None
    status: ProjectStatus | None = None


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
