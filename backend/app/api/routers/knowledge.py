from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.di import get_current_user, get_db
from app.db.models.knowledge import KnowledgeSource
from app.db.models.user import User
from app.domain.enums import KnowledgeSourceType
from app.evidence.storage import get_evidence_storage
from app.execution.tasks import ingest_knowledge_source_task
from app.rag.chroma_client import get_chroma_client
from app.rag.retriever import semantic_search
from app.schemas.knowledge import KnowledgeSourceOut, SemanticSearchRequest, SemanticSearchResult

router = APIRouter(prefix="/projects/{project_id}/knowledge", tags=["knowledge"])

_EXTENSION_MAP = {
    ".md": KnowledgeSourceType.MARKDOWN,
    ".markdown": KnowledgeSourceType.MARKDOWN,
    ".pdf": KnowledgeSourceType.PDF,
    ".docx": KnowledgeSourceType.DOCX,
    ".txt": KnowledgeSourceType.TXT,
    ".csv": KnowledgeSourceType.CSV,
    ".png": KnowledgeSourceType.IMAGE,
    ".jpg": KnowledgeSourceType.IMAGE,
    ".jpeg": KnowledgeSourceType.IMAGE,
    ".sql": KnowledgeSourceType.SQL,
    ".json": KnowledgeSourceType.OPENAPI,
    ".yaml": KnowledgeSourceType.SWAGGER,
    ".yml": KnowledgeSourceType.SWAGGER,
}


def _infer_source_type(filename: str) -> KnowledgeSourceType:
    lowered = filename.lower()

    # Both share the .json extension with plain OpenAPI specs — filename
    # convention is the only reliable signal without opening the file.
    if lowered.endswith(".json") and "postman" in lowered:
        return KnowledgeSourceType.POSTMAN
    if lowered.endswith((".png", ".jpg", ".jpeg")) and "screenshot" in lowered:
        return KnowledgeSourceType.SCREENSHOT

    for ext, source_type in _EXTENSION_MAP.items():
        if lowered.endswith(ext):
            return source_type
    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unsupported file type: {filename}")


@router.post("/upload", response_model=KnowledgeSourceOut, status_code=status.HTTP_201_CREATED)
async def upload_knowledge_source(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> KnowledgeSource:
    source_type = _infer_source_type(file.filename or "")
    raw = await file.read()

    storage_key = get_evidence_storage().put_bytes(
        f"knowledge/{project_id}", raw, file.content_type or "application/octet-stream"
    )

    source = KnowledgeSource(
        project_id=project_id,
        filename=file.filename or "unnamed",
        source_type=source_type,
        storage_key=storage_key,
        chroma_collection=get_chroma_client().collection_name(project_id),
    )
    session.add(source)
    await session.commit()

    ingest_knowledge_source_task.delay(str(source.id))
    return source


@router.get("", response_model=list[KnowledgeSourceOut])
async def list_knowledge_sources(
    project_id: uuid.UUID, session: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[KnowledgeSource]:
    result = await session.execute(select(KnowledgeSource).where(KnowledgeSource.project_id == project_id))
    return list(result.scalars().all())


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_source(
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    source = await session.get(KnowledgeSource, source_id)
    if source is None or source.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Knowledge source not found")
    await session.delete(source)
    await session.commit()


@router.post("/search", response_model=list[SemanticSearchResult])
async def search_knowledge(
    project_id: uuid.UUID,
    payload: SemanticSearchRequest,
    user: User = Depends(get_current_user),
) -> list[SemanticSearchResult]:
    return semantic_search(project_id, payload.query, payload.top_k)
