"""Ingestion pipeline: raw upload -> parse -> chunk -> embed -> store in Chroma.

Runs as a Celery task (see app.execution.tasks.ingest_knowledge_source) so
uploads return to the user in <2s while indexing happens in the background —
the KnowledgeSource.status field is how the frontend polls/streams progress.
"""
from __future__ import annotations

import uuid

from app.domain.enums import KnowledgeSourceType
from app.llm.embeddings import get_embedding_provider
from app.rag.chroma_client import get_chroma_client
from app.rag.chunker import chunk_text
from app.rag.parsers import get_parser


def ingest_document(
    project_id: uuid.UUID,
    knowledge_source_id: uuid.UUID,
    filename: str,
    source_type: KnowledgeSourceType,
    raw_bytes: bytes,
) -> int:
    """Returns the number of chunks stored. Raises on parse/embedding failure —
    the caller (Celery task) is responsible for recording KnowledgeSource.status."""
    parser = get_parser(source_type)
    text_blocks = parser(raw_bytes, filename)

    chunks: list[str] = []
    for block in text_blocks:
        chunks.extend(chunk_text(block))

    if not chunks:
        return 0

    embeddings = get_embedding_provider().embed(chunks)
    collection = get_chroma_client().get_or_create_collection(project_id)

    ids = [f"{knowledge_source_id}-{i}" for i in range(len(chunks))]
    metadatas = [
        {"filename": filename, "source_type": str(source_type), "knowledge_source_id": str(knowledge_source_id), "chunk_index": i}
        for i in range(len(chunks))
    ]

    collection.upsert(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
    return len(chunks)
