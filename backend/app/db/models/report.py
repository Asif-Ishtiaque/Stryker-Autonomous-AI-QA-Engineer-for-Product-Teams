from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid, pg_enum
from app.domain.enums import ReportFormat


class Report(TimestampMixin, Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    format: Mapped[ReportFormat] = mapped_column(pg_enum(ReportFormat, "report_format"))
    storage_key: Mapped[str] = mapped_column(String(1024))  # MinIO key for the rendered artifact

    run: Mapped["Run"] = relationship(back_populates="reports")


from app.db.models.run import Run  # noqa: E402
