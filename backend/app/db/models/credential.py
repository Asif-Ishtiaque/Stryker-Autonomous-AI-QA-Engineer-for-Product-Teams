"""CredentialProfile stores secrets for the Application Under Test (AUT).

Every secret field is stored pre-encrypted (see app.core.security.CredentialCipher)
by the service layer — the ORM layer never sees or handles plaintext, so a
DB dump alone can never leak a usable credential.
"""
from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid


class CredentialProfile(TimestampMixin, Base):
    __tablename__ = "credential_profiles"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=new_uuid)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(100))  # e.g. "Admin", "Manager", "Customer"

    encrypted_username: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    encrypted_password: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    encrypted_api_token: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    encrypted_bearer_token: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    encrypted_cookies: Mapped[str | None] = mapped_column(String(8192), nullable=True)
    encrypted_headers: Mapped[str | None] = mapped_column(String(8192), nullable=True)
    encrypted_env_vars: Mapped[str | None] = mapped_column(String(8192), nullable=True)

    # Reserved for future auth flows — not implemented in phase 1, present so the
    # schema doesn't need a breaking migration when they land.
    auth_metadata: Mapped[dict] = mapped_column(JSON, default=dict)  # mfa/otp/oauth config placeholders

    project: Mapped["Project"] = relationship(back_populates="credentials")


from app.db.models.project import Project  # noqa: E402
