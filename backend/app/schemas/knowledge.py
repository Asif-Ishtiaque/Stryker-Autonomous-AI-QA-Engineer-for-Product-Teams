from __future__ import annotations

import uuid

from pydantic import BaseModel

from app.domain.enums import KnowledgeIndexStatus, KnowledgeSourceType


class KnowledgeSourceOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    filename: str
    source_type: KnowledgeSourceType
    status: KnowledgeIndexStatus
    chunk_count: int
    error_message: str | None

    model_config = {"from_attributes": True}


class SemanticSearchRequest(BaseModel):
    query: str
    top_k: int = 8


class SemanticSearchResult(BaseModel):
    source_filename: str
    chunk_text: str
    score: float
    metadata: dict
