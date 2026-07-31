from __future__ import annotations

import datetime as dt
import uuid
from enum import Enum as _PyEnum
from typing import TypeVar

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

EnumT = TypeVar("EnumT", bound=_PyEnum)


class Base(DeclarativeBase):
    pass


def pg_enum(enum_cls: type[EnumT], name: str) -> Enum:
    """Builds a Postgres ENUM column type whose stored labels are the members' `.value`s
    (e.g. "owner"), not their `.name`s (e.g. "OWNER").

    Every enum in app.domain.enums is a StrEnum with a lowercase `.value` distinct from its
    uppercase `.name`. sqlalchemy.Enum(some_enum_cls) defaults to binding/storing `.name` unless
    told otherwise via `values_callable` — which would silently mismatch the lowercase labels the
    Alembic migration (alembic/versions/0001_initial_schema.py) actually creates in Postgres,
    breaking every insert/update through an enum column (e.g. "invalid input value for enum
    run_status: \"QUEUED\"") against a real, migrated database.
    """
    return Enum(enum_cls, name=name, values_callable=lambda cls: [e.value for e in cls])


class TimestampMixin:
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


def new_uuid() -> uuid.UUID:
    return uuid.uuid4()
