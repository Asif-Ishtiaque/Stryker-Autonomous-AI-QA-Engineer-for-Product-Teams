from __future__ import annotations

import uuid

from sqlalchemy import JSON, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid


class Requirement(TimestampMixin, Base):
    """A plain-English behavior the user wants Stryker to verify.

    `ai_analysis` stores the RequirementAgent's structured read of the text —
    inferred validations, risks, edge cases, confidence — cached so re-running
    the same requirement doesn't require re-parsing it against the LLM.
    """

    __tablename__ = "requirements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    credential_profile_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("credential_profiles.id", ondelete="SET NULL"), nullable=True
    )
    text: Mapped[str] = mapped_column(Text)
    ai_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="requirements")
    runs: Mapped[list["Run"]] = relationship(back_populates="requirement")


from app.db.models.project import Project  # noqa: E402
from app.db.models.run import Run  # noqa: E402
