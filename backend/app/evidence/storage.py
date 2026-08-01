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
        # Separate client for presigned URLs, which the BROWSER loads directly — it must sign
        # for the browser-reachable host (minio_public_endpoint), not the internal Docker
        # service name (minio_endpoint) the backend itself uses for put/get. See the comment
        # on minio_public_endpoint in app.core.config for why this can't just be a URL rewrite.
        #
        # region="us-east-1" is required here, not optional: without an explicit region,
        # minio-py's presigned_get_object() first calls GetBucketLocation against the client's
        # configured endpoint to resolve it — a real network round-trip. From inside this
        # container, minio_public_endpoint (localhost:9000) resolves to the container's own
        # loopback, where nothing is listening, so that lookup fails with connection-refused
        # and the whole call raises. Passing the region explicitly (matching what the bucket
        # was actually created with) skips that lookup entirely — signing becomes pure local
        # computation, so this client never needs to be reachable at all.
        self._public_client = Minio(
            settings.minio_public_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
            region="us-east-1",
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

        return self._public_client.presigned_get_object(
            self._bucket, key, expires=dt.timedelta(seconds=expires_seconds)
        )


@lru_cache
def get_evidence_storage() -> EvidenceStorage:
    return EvidenceStorage(get_settings())
