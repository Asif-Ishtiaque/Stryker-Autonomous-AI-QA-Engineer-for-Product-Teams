from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.models.run import Run, Step
from app.db.repositories.base import BaseRepository


class RunRepository(BaseRepository[Run]):
    model = Run

    async def get_with_steps(self, run_id) -> Run | None:
        stmt = (
            select(Run)
            .where(Run.id == run_id)
            # A string attribute name here ("evidence") raises
            # `ArgumentError: Strings are not accepted for attribute names in loader options`
            # on current SQLAlchemy — must be the class-bound Step.evidence.
            .options(selectinload(Run.steps).selectinload(Step.evidence))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_project(self, project_id) -> list[Run]:
        # RunOut serializes `steps` (and each step's `evidence`) — without eager loading them,
        # FastAPI's (synchronous) response serialization triggers an async lazy-load in a context
        # that can't await it (`MissingGreenlet`).
        stmt = (
            select(Run)
            .where(Run.project_id == project_id)
            .order_by(Run.created_at.desc())
            .options(selectinload(Run.steps).selectinload(Step.evidence))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
