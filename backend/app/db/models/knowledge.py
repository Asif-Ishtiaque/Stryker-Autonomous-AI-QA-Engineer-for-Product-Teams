from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid, pg_enum
from app.domain.enums import KnowledgeIndexStatus, KnowledgeSourceType


class KnowledgeSource(TimestampMixin, Base):
    __tablename__ = "knowledge_sources"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(512))
    source_type: Mapped[KnowledgeSourceType] = mapped_column(pg_enum(KnowledgeSourceType, "knowledge_source_type"))
    storage_key: Mapped[str] = mapped_column(String(1024))  # MinIO object key for the raw upload
    chroma_collection: Mapped[str] = mapped_column(String(255))
    status: Mapped[KnowledgeIndexStatus] = mapped_column(
        pg_enum(KnowledgeIndexStatus, "knowledge_index_status"), default=KnowledgeIndexStatus.PENDING
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="knowledge_sources")


from app.db.models.project import Project  # noqa: E402
