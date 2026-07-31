from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.domain.enums import ReportFormat


class ReportOut(BaseModel):
    id: uuid.UUID
    run_id: uuid.UUID
    format: ReportFormat
    storage_key: str

    model_config = {"from_attributes": True}


class ReportGenerateRequest(BaseModel):
    formats: list[ReportFormat] = [ReportFormat.MARKDOWN, ReportFormat.JSON]
