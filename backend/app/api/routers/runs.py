from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.di import get_db, get_owned_project
from app.db.models.project import Project
from app.db.models.requirement import Requirement
from app.db.models.run import Run
from app.db.repositories.runs import RunRepository
from app.domain.enums import RunStatus
from app.evidence.storage import get_evidence_storage
from app.execution.celery_app import celery_app
from app.execution.tasks import run_requirement_task
from app.schemas.run import RunCreate, RunOut

router = APIRouter(prefix="/projects/{project_id}/runs", tags=["runs"])


@router.post("", response_model=RunOut, status_code=status.HTTP_201_CREATED)
async def create_run(
    payload: RunCreate,
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_db),
) -> Run:
    requirement = await session.get(Requirement, payload.requirement_id)
    if requirement is None or requirement.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Requirement not found")

    run = Run(project_id=project.id, requirement_id=payload.requirement_id, status=RunStatus.QUEUED)
    session.add(run)
    await session.commit()
    # RunOut serializes `steps` (and each step's `evidence`). That relationship was never
    # loaded on this brand-new object, and accessing it lazily during (synchronous) response
    # serialization raises `MissingGreenlet` under AsyncSession — there's no implicit IO on a
    # sync attribute access the way there is with a sync Session. Load it explicitly first;
    # it's always empty for a just-created run, but it must be *known* empty, not unloaded.
    await session.refresh(run, attribute_names=["steps"])

    # Pin the Celery task_id to the run's own id (rather than letting Celery
    # generate one) so POST /{run_id}/cancel can revoke the exact in-flight
    # task by that same id.
    run_requirement_task.apply_async(args=[str(run.id)], task_id=str(run.id))
    return run


@router.get("", response_model=list[RunOut])
async def list_runs(project: Project = Depends(get_owned_project), session: AsyncSession = Depends(get_db)) -> list[Run]:
    return await RunRepository(session).list_for_project(project.id)


@router.get("/{run_id}", response_model=RunOut)
async def get_run(
    run_id: uuid.UUID, project: Project = Depends(get_owned_project), session: AsyncSession = Depends(get_db)
) -> Run:
    run = await RunRepository(session).get_with_steps(run_id)
    if run is None or run.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    return run


@router.post("/{run_id}/cancel", response_model=RunOut)
async def cancel_run(
    run_id: uuid.UUID, project: Project = Depends(get_owned_project), session: AsyncSession = Depends(get_db)
) -> Run:
    run = await session.get(Run, run_id)
    if run is None or run.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    if run.status in (RunStatus.PASSED, RunStatus.FAILED, RunStatus.ERRORED, RunStatus.CANCELLED):
        raise HTTPException(status.HTTP_409_CONFLICT, "Run already finished")
    celery_app.control.revoke(str(run_id), terminate=True)
    run.status = RunStatus.CANCELLED
    await session.commit()
    # See the matching comment in create_run(): RunOut serializes `steps`, which is never loaded
    # on an object fetched via plain session.get() — must load it explicitly before it's handed
    # to (synchronous) response serialization.
    await session.refresh(run, attribute_names=["steps"])
    return run


@router.get("/{run_id}/evidence/{evidence_id}/url")
async def get_evidence_url(
    run_id: uuid.UUID,
    evidence_id: uuid.UUID,
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    from app.db.models.run import Evidence, Step

    run = await session.get(Run, run_id)
    if run is None or run.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    evidence = await session.get(Evidence, evidence_id)
    if evidence is None or evidence.storage_key is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidence not found or has no binary artifact")
    step = await session.get(Step, evidence.step_id)
    if step is None or step.run_id != run_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Evidence does not belong to this run")
    return {"url": get_evidence_storage().presigned_url(evidence.storage_key)}
