from __future__ import annotations

import uuid

from pydantic import BaseModel


class RequirementCreate(BaseModel):
    text: str
    credential_profile_id: uuid.UUID | None = None


class RequirementUpdate(BaseModel):
    credential_profile_id: uuid.UUID | None = None


class RequirementAnalysis(BaseModel):
    """Structured output of the RequirementAgent."""

    understood_intent: str
    expected_outcomes: list[str]
    inferred_validations: list[str]
    identified_risks: list[str]
    predicted_edge_cases: list[str]
    confidence: float


class RequirementOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    text: str
    credential_profile_id: uuid.UUID | None
    ai_analysis: RequirementAnalysis | None

    model_config = {"from_attributes": True}
