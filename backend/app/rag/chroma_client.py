"""ChromaDB access — one collection per project, so knowledge never leaks
across projects and a project delete can drop its collection outright.
"""
from __future__ import annotations

import uuid
from functools import lru_cache

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings


class ChromaClientWrapper:
    def __init__(self, host: str, port: int, collection_prefix: str) -> None:
        self._client = chromadb.HttpClient(host=host, port=port, settings=ChromaSettings(anonymized_telemetry=False))
        self._prefix = collection_prefix

    def collection_name(self, project_id: uuid.UUID) -> str:
        return f"{self._prefix}_{project_id.hex}"

    def get_or_create_collection(self, project_id: uuid.UUID):
        return self._client.get_or_create_collection(name=self.collection_name(project_id))

    def delete_collection(self, project_id: uuid.UUID) -> None:
        try:
            self._client.delete_collection(self.collection_name(project_id))
        except Exception:
            pass


@lru_cache
def get_chroma_client() -> ChromaClientWrapper:
    settings = get_settings()
    return ChromaClientWrapper(settings.chroma_host, settings.chroma_port, settings.chroma_collection_prefix)
