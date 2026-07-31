"""MinIO (S3-compatible) client wrapper for evidence artifacts and raw
knowledge-source uploads. One bucket, keys namespaced by kind/id so nothing
else needs to know MinIO's API surface.
"""
from __future__ import annotations

import io
import uuid
from functools import lru_cache

from minio import Minio

from app.core.config import Settings, get_settings


class EvidenceStorage:
    def __init__(self, settings: Settings) -> None:
        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self._bucket = settings.minio_evidence_bucket
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    def put_bytes(self, key_prefix: str, data: bytes, content_type: str, extension: str = "") -> str:
        key = f"{key_prefix}/{uuid.uuid4()}{extension}"
        self._client.put_object(self._bucket, key, io.BytesIO(data), length=len(data), content_type=content_type)
        return key

    def get_bytes(self, key: str) -> bytes:
        response = self._client.get_object(self._bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def presigned_url(self, key: str, expires_seconds: int = 3600) -> str:
        import datetime as dt

        return self._client.presigned_get_object(self._bucket, key, expires=dt.timedelta(seconds=expires_seconds))


@lru_cache
def get_evidence_storage() -> EvidenceStorage:
    return EvidenceStorage(get_settings())
