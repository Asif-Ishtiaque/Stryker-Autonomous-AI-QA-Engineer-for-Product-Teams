from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.requirement_agent import run_requirement_agent
from app.core.di import get_db, get_owned_project
from app.db.models.project import Project
from app.db.models.requirement import Requirement
from app.llm.registry import get_llm_provider
from app.rag.retriever import context_snippets_for_requirement
from app.schemas.requirement import RequirementAnalysis, RequirementCreate, RequirementOut

router = APIRouter(prefix="/projects/{project_id}/requirements", tags=["requirements"])


@router.post("", response_model=RequirementOut, status_code=status.HTTP_201_CREATED)
async def create_requirement(
    payload: RequirementCreate,
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_db),
) -> Requirement:
    requirement = Requirement(project_id=project.id, **payload.model_dump())
    session.add(requirement)
    await session.commit()
    return requirement


@router.get("", response_model=list[RequirementOut])
async def list_requirements(
    project: Project = Depends(get_owned_project), session: AsyncSession = Depends(get_db)
) -> list[Requirement]:
    result = await session.execute(select(Requirement).where(Requirement.project_id == project.id))
    return list(result.scalars().all())


@router.get("/{requirement_id}", response_model=RequirementOut)
async def get_requirement(
    requirement_id: uuid.UUID,
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_db),
) -> Requirement:
    requirement = await session.get(Requirement, requirement_id)
    if requirement is None or requirement.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Requirement not found")
    return requirement


@router.post("/{requirement_id}/analyze", response_model=RequirementAnalysis)
async def analyze_requirement(
    requirement_id: uuid.UUID,
    project: Project = Depends(get_owned_project),
    session: AsyncSession = Depends(get_db),
) -> RequirementAnalysis:
    """Runs only the RequirementAgent (<5s) so the UI can show the AI's
    understanding — expected outcomes, inferred validations, risks, edge
    cases, confidence — before the user commits to a full Run."""
    requirement = await session.get(Requirement, requirement_id)
    if requirement is None or requirement.project_id != project.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Requirement not found")

    knowledge_context = context_snippets_for_requirement(project.id, requirement.text)
    state = {
        "requirement_text": requirement.text,
        "platform": str(project.platform) if project else "web",
        "knowledge_context": knowledge_context,
    }
    result_state = await run_requirement_agent(state, get_llm_provider())

    analysis = RequirementAnalysis(
        understood_intent=result_state["understood_intent"],
        expected_outcomes=result_state["expected_outcomes"],
        inferred_validations=result_state["inferred_validations"],
        identified_risks=result_state["identified_risks"],
        predicted_edge_cases=result_state["predicted_edge_cases"],
        confidence=result_state["requirement_confidence"],
    )
    requirement.ai_analysis = analysis.model_dump()
    await session.commit()
    return analysis
