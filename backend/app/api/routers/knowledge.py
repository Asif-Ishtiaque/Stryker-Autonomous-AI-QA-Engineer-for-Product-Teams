from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.di import get_db, get_owned_project
from app.db.models.knowledge import KnowledgeSource
from app.db.models.project import Project
from app.domain.enums import KnowledgeSourceType
from app.evidence.storage import get_evidence_storage
from app.execution.tasks import ingest_knowledge_source_task
from app.rag.chroma_client import get_chroma_client
from app.rag.retriever import semantic_search
from app.schemas.knowledge import KnowledgeSourceOut, SemanticSearchRequest, SemanticSearchResult

router = APIRouter(prefix="/projects/{project_id}/knowledge", tags=["knowledge"])

# No limit existed before this: `await file.read()` pulled the entire upload into memory
# unconditionally, so a large-enough file (or several concurrent ones) could OOM the API
# process. Reading in bounded chunks means a too-large upload is rejected well before that
# much memory is ever held, rather than after the fact.
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
_UPLOAD_CHUNK_BYTES = 1024 * 1024

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


async def _read_bounded(file: UploadFile, max_bytes: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(_UPLOAD_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                f"File exceeds the {max_bytes // (1024 * 1024)}MB upload limit",
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/upload", response_model=KnowledgeSourceOut, status_code=status.HTTP_201_CREATED)
async def upload_knowledge_source(
    file: UploadFile = File(...),
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_db),
) -> KnowledgeSource:
    source_type = _infer_source_type(file.filename or "")
    raw = await _read_bounded(file, _MAX_UPLOAD_BYTES)

    storage_key = get_evidence_storage().put_bytes(
        f"knowledge/{project.id}", raw, file.content_type or "application/octet-stream"
    )

    source = KnowledgeSource(
        project_id=project.id,
        filename=file.filename or "unnamed",
        source_type=source_type,
        storage_key=storage_key,
        chroma_collection=get_chroma_client().collection_name(project.id),
    )
    session.add(source)
    await session.commit()

    ingest_knowledge_source_task.delay(str(source.id))
    return source


@router.get("", response_model=list[KnowledgeSourceOut])
async def list_knowledge_sources(
    project: Project = Depends(get_owned_project), session: AsyncSession = Depends(get_db)
) -> list[KnowledgeSource]:
    result = await session.execute(select(KnowledgeSource).where(KnowledgeSource.project_id == project.id))
    return list(result.scalars().all())


@router.delete("/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_source(
    source_id: uuid.UUID,
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_db),
) -> None:
    source = await session.get(KnowledgeSource, source_id)
    if source is None or source.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Knowledge source not found")
    await session.delete(source)
    await session.commit()


@router.post("/search", response_model=list[SemanticSearchResult])
async def search_knowledge(
    payload: SemanticSearchRequest,
    project: Project = Depends(get_owned_project),
) -> list[SemanticSearchResult]:
    return semantic_search(project.id, payload.query, payload.top_k)
