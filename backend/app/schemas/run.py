from __future__ import annotations

import datetime as dt
import uuid

from pydantic import BaseModel

from app.domain.enums import EvidenceType, RunStatus, StepStatus


class RunCreate(BaseModel):
    requirement_id: uuid.UUID


class RootCauseAnalysis(BaseModel):
    """Structured output of the ComparatorAgent's failure analysis — see
    app.agents.comparator_agent.ROOT_CAUSE_SCHEMA for the LLM-facing shape
    this mirrors."""

    observed_behavior: str
    expected_behavior: str
    evidence: list[str]
    root_cause: str
    confidence: float
    suggested_fix: str
    affected_component: str
    severity: str
    likely_owner: str


class EvidenceOut(BaseModel):
    id: uuid.UUID
    evidence_type: EvidenceType
    storage_key: str | None
    inline_data: dict | None
    content_type: str | None

    model_config = {"from_attributes": True}


class StepOut(BaseModel):
    id: uuid.UUID
    sequence: int
    name: str
    action_type: str
    parameters: dict
    status: StepStatus
    retry_count: int
    started_at: dt.datetime | None
    finished_at: dt.datetime | None
    result: dict | None
    error_message: str | None
    evidence: list[EvidenceOut] = []

    model_config = {"from_attributes": True}


class RunOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    requirement_id: uuid.UUID
    status: RunStatus
    plan: dict | None
    validation_checklist: dict | None
    confidence_score: float | None
    severity: str | None
    root_cause_hypothesis: str | None
    root_cause_analysis: RootCauseAnalysis | None
    error_message: str | None
    report_markdown: str | None
    started_at: dt.datetime | None
    finished_at: dt.datetime | None
    duration_ms: int | None
    steps: list[StepOut] = []

    model_config = {"from_attributes": True}


class RunStepEvent(BaseModel):
    """Payload pushed over the run's WebSocket channel as execution progresses."""

    run_id: uuid.UUID
    step_id: uuid.UUID | None = None
    run_status: RunStatus
    step_status: StepStatus | None = None
    sequence: int | None = None
    name: str | None = None
    message: str | None = None
    confidence_score: float | None = None
