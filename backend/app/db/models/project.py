from __future__ import annotations

import uuid

from sqlalchemy import ARRAY, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid, pg_enum
from app.domain.enums import Platform, ProjectEnvironment, ProjectStatus


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    platform: Mapped[Platform] = mapped_column(pg_enum(Platform, "platform"))
    environment: Mapped[ProjectEnvironment] = mapped_column(
        pg_enum(ProjectEnvironment, "project_environment"), default=ProjectEnvironment.STAGING
    )
    base_url: Mapped[str] = mapped_column(String(1024))
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    status: Mapped[ProjectStatus] = mapped_column(pg_enum(ProjectStatus, "project_status"), default=ProjectStatus.ACTIVE)

    knowledge_sources: Mapped[list["KnowledgeSource"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    credentials: Mapped[list["CredentialProfile"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    requirements: Mapped[list["Requirement"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    runs: Mapped[list["Run"]] = relationship(back_populates="project", cascade="all, delete-orphan")


from app.db.models.credential import CredentialProfile  # noqa: E402
from app.db.models.knowledge import KnowledgeSource  # noqa: E402
from app.db.models.requirement import Requirement  # noqa: E402
from app.db.models.run import Run  # noqa: E402
