"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-07-31

Hand-written to mirror app/db/models/*.py exactly (no live database was
available in the environment this was authored in to run
`alembic revision --autogenerate`). If you have a running Postgres, it is
worth a one-time sanity check: `alembic upgrade head` then
`alembic check` (or a fresh `--autogenerate` diff, which should come back
empty) to confirm this matches the ORM models bit-for-bit.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]


def upgrade() -> None:
    # create_type=False on every enum below: they're created explicitly, once, in the loop
    # right after this block. Leaving the default (create_type=True) makes each op.create_table
    # call below try to CREATE TYPE again for that same column's enum, which raises
    # asyncpg.exceptions.DuplicateObjectError ("type already exists") the second time any given
    # enum type is used in more than one place — Alembic's create_table DDL, unlike
    # `metadata.create_all`, doesn't check-first against types this migration already created.
    user_role = pg.ENUM("owner", "admin", "member", "viewer", name="user_role", create_type=False)
    platform = pg.ENUM("web", "rest_api", "graphql", "mobile", "desktop", name="platform", create_type=False)
    project_environment = pg.ENUM(
        "production", "staging", "qa", "development", name="project_environment", create_type=False
    )
    project_status = pg.ENUM("active", "archived", "paused", name="project_status", create_type=False)
    knowledge_source_type = pg.ENUM(
        "markdown", "pdf", "docx", "txt", "csv", "image", "swagger", "openapi", "postman", "sql",
        "screenshot", "video", name="knowledge_source_type", create_type=False,
    )
    knowledge_index_status = pg.ENUM(
        "pending", "processing", "indexed", "failed", name="knowledge_index_status", create_type=False
    )
    run_status = pg.ENUM(
        "queued", "planning", "running", "retrying", "validating", "passed", "failed", "errored", "cancelled",
        name="run_status", create_type=False,
    )
    step_status = pg.ENUM(
        "waiting", "running", "retrying", "passed", "failed", "skipped", name="step_status", create_type=False
    )
    evidence_type = pg.ENUM(
        "screenshot", "video", "console_log", "network_log", "dom_snapshot", "accessibility_tree",
        "api_request", "api_response", "timing", name="evidence_type", create_type=False,
    )
    report_format = pg.ENUM("markdown", "pdf", "json", "jira", name="report_format", create_type=False)

    bind = op.get_bind()
    for enum_type in (
        user_role, platform, project_environment, project_status, knowledge_source_type,
        knowledge_index_status, run_status, step_status, evidence_type, report_format,
    ):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default="member"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        *_timestamps(),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "projects",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=False, server_default=""),
        sa.Column("platform", platform, nullable=False),
        sa.Column("environment", project_environment, nullable=False, server_default="staging"),
        sa.Column("base_url", sa.String(1024), nullable=False),
        sa.Column("tags", pg.ARRAY(sa.String), nullable=False, server_default="{}"),
        sa.Column("status", project_status, nullable=False, server_default="active"),
        *_timestamps(),
    )

    op.create_table(
        "credential_profiles",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", pg.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("encrypted_username", sa.String(2048), nullable=True),
        sa.Column("encrypted_password", sa.String(2048), nullable=True),
        sa.Column("encrypted_api_token", sa.String(4096), nullable=True),
        sa.Column("encrypted_bearer_token", sa.String(4096), nullable=True),
        sa.Column("encrypted_cookies", sa.String(8192), nullable=True),
        sa.Column("encrypted_headers", sa.String(8192), nullable=True),
        sa.Column("encrypted_env_vars", sa.String(8192), nullable=True),
        sa.Column("auth_metadata", pg.JSON, nullable=False, server_default="{}"),
        *_timestamps(),
    )

    op.create_table(
        "knowledge_sources",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", pg.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("source_type", knowledge_source_type, nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        sa.Column("chroma_collection", sa.String(255), nullable=False),
        sa.Column("status", knowledge_index_status, nullable=False, server_default="pending"),
        sa.Column("chunk_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text, nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "requirements",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", pg.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "credential_profile_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("credential_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("ai_analysis", pg.JSON, nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "runs",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("project_id", pg.UUID(as_uuid=True), sa.ForeignKey("projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requirement_id", pg.UUID(as_uuid=True), sa.ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", run_status, nullable=False, server_default="queued"),
        sa.Column("plan", pg.JSON, nullable=True),
        sa.Column("validation_checklist", pg.JSON, nullable=True),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("root_cause_hypothesis", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("report_markdown", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "steps",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", pg.UUID(as_uuid=True), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("parameters", pg.JSON, nullable=False, server_default="{}"),
        sa.Column("status", step_status, nullable=False, server_default="waiting"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("result", pg.JSON, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "evidence",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("step_id", pg.UUID(as_uuid=True), sa.ForeignKey("steps.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evidence_type", evidence_type, nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=True),
        sa.Column("inline_data", pg.JSON, nullable=True),
        sa.Column("content_type", sa.String(100), nullable=True),
        *_timestamps(),
    )

    op.create_table(
        "reports",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", pg.UUID(as_uuid=True), sa.ForeignKey("runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format", report_format, nullable=False),
        sa.Column("storage_key", sa.String(1024), nullable=False),
        *_timestamps(),
    )


def downgrade() -> None:
    op.drop_table("reports")
    op.drop_table("evidence")
    op.drop_table("steps")
    op.drop_table("runs")
    op.drop_table("requirements")
    op.drop_table("knowledge_sources")
    op.drop_table("credential_profiles")
    op.drop_table("projects")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    for name in (
        "report_format", "evidence_type", "step_status", "run_status", "knowledge_index_status",
        "knowledge_source_type", "project_status", "project_environment", "platform", "user_role",
    ):
        pg.ENUM(name=name).drop(bind, checkfirst=True)
