from __future__ import annotations

import uuid

from sqlalchemy import func, select

from app.db.models.project import Project
from app.db.models.requirement import Requirement
from app.db.models.run import Run
from app.db.repositories.base import BaseRepository
from app.domain.enums import RunStatus


class ProjectRepository(BaseRepository[Project]):
    model = Project

    async def stats(self, project_id: uuid.UUID) -> dict:
        requirement_count = (
            await self.session.execute(
                select(func.count()).select_from(Requirement).where(Requirement.project_id == project_id)
            )
        ).scalar_one()

        runs = (
            await self.session.execute(select(Run).where(Run.project_id == project_id))
        ).scalars().all()

        run_count = len(runs)
        passed = sum(1 for r in runs if r.status == RunStatus.PASSED)
        failed = sum(1 for r in runs if r.status in (RunStatus.FAILED, RunStatus.ERRORED))
        durations = [r.duration_ms for r in runs if r.duration_ms is not None]
        confidences = [r.confidence_score for r in runs if r.confidence_score is not None]

        return {
            "requirement_count": requirement_count,
            "run_count": run_count,
            "pass_rate": (passed / run_count) if run_count else 0.0,
            "average_duration_ms": (sum(durations) / len(durations)) if durations else None,
            "open_bugs": failed,
            "average_confidence": (sum(confidences) / len(confidences)) if confidences else None,
        }
