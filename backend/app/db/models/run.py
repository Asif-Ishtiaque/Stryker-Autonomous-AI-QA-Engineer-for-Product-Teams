from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid, pg_enum
from app.domain.enums import EvidenceType, RunStatus, StepStatus


class Run(TimestampMixin, Base):
    """One execution of a Requirement: plan -> execute -> validate -> report."""

    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    requirement_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("requirements.id", ondelete="CASCADE"))
    status: Mapped[RunStatus] = mapped_column(pg_enum(RunStatus, "run_status"), default=RunStatus.QUEUED)

    plan: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # PlannerAgent output
    validation_checklist: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity: Mapped[str | None] = mapped_column(String(20), nullable=True)
    root_cause_hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    report_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Explicit timezone=True: app.execution.tasks always assigns tz-aware
    # datetime.now(dt.timezone.utc). Without it, this column maps to
    # TIMESTAMP WITHOUT TIME ZONE and asyncpg refuses to bind an aware
    # datetime into it (DataError: "can't subtract offset-naive and
    # offset-aware datetimes") — the run pipeline could never persist a
    # started/finished run against a real Postgres database.
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="runs")
    requirement: Mapped["Requirement"] = relationship(back_populates="runs")
    steps: Mapped[list["Step"]] = relationship(back_populates="run", cascade="all, delete-orphan", order_by="Step.sequence")
    reports: Mapped[list["Report"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class Step(TimestampMixin, Base):
    """A single planned action within a Run (e.g. 'Navigate to /invoices')."""

    __tablename__ = "steps"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    sequence: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(255))
    action_type: Mapped[str] = mapped_column(String(50))  # navigate, click, fill, assert, api_call, ...
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[StepStatus] = mapped_column(pg_enum(StepStatus, "step_status"), default=StepStatus.WAITING)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped["Run"] = relationship(back_populates="steps")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="step", cascade="all, delete-orphan")


class Evidence(TimestampMixin, Base):
    """A single captured artifact tied to a Step (screenshot, network log, ...)."""

    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    step_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("steps.id", ondelete="CASCADE"))
    evidence_type: Mapped[EvidenceType] = mapped_column(pg_enum(EvidenceType, "evidence_type"))
    storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)  # MinIO key for binary artifacts
    inline_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # small structured payloads (timing, headers)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    step: Mapped["Step"] = relationship(back_populates="evidence")


from app.db.models.project import Project  # noqa: E402
from app.db.models.report import Report  # noqa: E402
from app.db.models.requirement import Requirement  # noqa: E402
