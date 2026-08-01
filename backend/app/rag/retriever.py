from __future__ import annotations

import uuid

from app.core.logging import get_logger
from app.llm.embeddings import get_embedding_provider
from app.rag.chroma_client import get_chroma_client
from app.schemas.knowledge import SemanticSearchResult

logger = get_logger(__name__)


def semantic_search(project_id: uuid.UUID, query: str, top_k: int = 8) -> list[SemanticSearchResult]:
    collection = get_chroma_client().get_or_create_collection(project_id)
    if collection.count() == 0:
        return []

    embedding = get_embedding_provider().embed([query])[0]
    results = collection.query(query_embeddings=[embedding], n_results=min(top_k, collection.count()))

    out: list[SemanticSearchResult] = []
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for doc, meta, distance in zip(documents, metadatas, distances, strict=False):
        out.append(
            SemanticSearchResult(
                source_filename=(meta or {}).get("filename", "unknown"),
                chunk_text=doc,
                score=1.0 - distance,
                metadata=meta or {},
            )
        )
    return out


def context_snippets_for_requirement(project_id: uuid.UUID, requirement_text: str, top_k: int = 5) -> list[str]:
    """Best-effort knowledge-base enrichment for a run.

    Called from inside the run pipeline, before the try/except that guards
    graph execution (see app.execution.tasks) — a knowledge-base outage must
    never take down a run that doesn't otherwise depend on it. A deliberate
    user-initiated search (the semantic_search Knowledge tab endpoint) still
    raises normally, since silently returning nothing there would just look
    like "no results" instead of a real outage.
    """
    try:
        return [r.chunk_text for r in semantic_search(project_id, requirement_text, top_k)]
    except Exception as exc:  # noqa: BLE001 — degrade to no context, never abort the run
        logger.warning("context_snippets_for_requirement.failed", project_id=str(project_id), error=str(exc))
        return []
