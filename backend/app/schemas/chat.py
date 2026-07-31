from __future__ import annotations

import uuid

from pydantic import BaseModel


class ChatMessageRequest(BaseModel):
    project_id: uuid.UUID
    message: str
    conversation_id: uuid.UUID | None = None


class ChatSource(BaseModel):
    kind: str  # "run" | "knowledge"
    ref_id: uuid.UUID
    snippet: str


class ChatMessageResponse(BaseModel):
    conversation_id: uuid.UUID
    answer: str
    sources: list[ChatSource]
