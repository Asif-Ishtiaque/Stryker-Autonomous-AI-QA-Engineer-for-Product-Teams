"""Local embeddings via sentence-transformers — no network call, no API key,
so RAG ingestion works fully offline. Model is configurable (BGE, Nomic, or
any sentence-transformers-compatible checkpoint) via EMBEDDING_MODEL.
"""
from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings


class SentenceTransformerEmbeddingProvider:
    def __init__(self, model_name: str, device: str = "cpu") -> None:
        self._model = SentenceTransformer(model_name, device=device)

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = self._model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        return vectors.tolist()

    @property
    def dimensions(self) -> int:
        return self._model.get_sentence_embedding_dimension()


@lru_cache
def get_embedding_provider() -> SentenceTransformerEmbeddingProvider:
    settings = get_settings()
    return SentenceTransformerEmbeddingProvider(settings.embedding_model, settings.embedding_device)
