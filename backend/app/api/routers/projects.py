from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.di import get_current_user, get_db, get_owned_project
from app.db.models.project import Project
from app.db.models.user import User
from app.db.repositories.projects import ProjectRepository
from app.rag.chroma_client import get_chroma_client
from app.schemas.project import ProjectCreate, ProjectOut, ProjectStats, ProjectUpdate

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate, session: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> Project:
    project = Project(owner_id=user.id, **payload.model_dump())
    session.add(project)
    await session.commit()
    return project


@router.get("", response_model=list[ProjectOut])
async def list_projects(session: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)) -> list[Project]:
    return await ProjectRepository(session).list(owner_id=user.id)


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project: Project = Depends(get_owned_project)) -> Project:
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    payload: ProjectUpdate,
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_db),
) -> Project:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    await session.commit()
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(project: Project = Depends(get_owned_project), session: AsyncSession = Depends(get_db)) -> None:
    project_id = project.id
    await session.delete(project)
    await session.commit()
    get_chroma_client().delete_collection(project_id)


@router.get("/{project_id}/stats", response_model=ProjectStats)
async def project_stats(project: Project = Depends(get_owned_project), session: AsyncSession = Depends(get_db)) -> dict:
    return await ProjectRepository(session).stats(project.id)
