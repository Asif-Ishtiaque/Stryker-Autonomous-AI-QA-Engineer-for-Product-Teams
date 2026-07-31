from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.di import get_current_user, get_db
from app.db.models.report import Report
from app.db.models.run import Run
from app.db.models.user import User
from app.domain.enums import ReportFormat
from app.evidence.storage import get_evidence_storage
from app.reports.jira_report import render_jira
from app.reports.pdf_report import render_pdf
from app.schemas.report import ReportGenerateRequest, ReportOut

router = APIRouter(prefix="/projects/{project_id}/runs/{run_id}/reports", tags=["reports"])


@router.get("", response_model=list[ReportOut])
async def list_reports(
    project_id: uuid.UUID, run_id: uuid.UUID, session: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> list[Report]:
    result = await session.execute(select(Report).where(Report.run_id == run_id))
    return list(result.scalars().all())


@router.post("", response_model=list[ReportOut], status_code=status.HTTP_201_CREATED)
async def generate_reports(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    payload: ReportGenerateRequest,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[Report]:
    run = await session.get(Run, run_id)
    if run is None or run.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Run not found")
    if run.report_markdown is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Run has not finished producing a report yet")

    storage = get_evidence_storage()
    created: list[Report] = []

    for fmt in payload.formats:
        if fmt == ReportFormat.PDF:
            pdf_bytes = render_pdf(run.report_markdown, title=f"Stryker Report {run.id}")
            key = storage.put_bytes(f"reports/{run.id}", pdf_bytes, "application/pdf", ".pdf")
        elif fmt == ReportFormat.JIRA:
            from app.db.models.requirement import Requirement

            requirement = await session.get(Requirement, run.requirement_id)
            report_json = {
                "requirement_text": requirement.text if requirement else None,
                "final_status": str(run.status),
                "confidence_score": run.confidence_score,
                "severity": run.severity,
                "root_cause_hypothesis": run.root_cause_hypothesis,
                "validation_checklist": run.validation_checklist,
                "plan": (run.plan or {}).get("steps", []),
            }
            jira_text = render_jira(report_json)
            key = storage.put_bytes(f"reports/{run.id}", jira_text.encode(), "text/plain", ".jira.txt")
        elif fmt == ReportFormat.MARKDOWN:
            key = storage.put_bytes(f"reports/{run.id}", run.report_markdown.encode(), "text/markdown", ".md")
        else:
            continue

        report = Report(run_id=run.id, format=fmt, storage_key=key)
        session.add(report)
        created.append(report)

    await session.commit()
    return created


@router.get("/{report_id}/url")
async def get_report_url(
    project_id: uuid.UUID,
    run_id: uuid.UUID,
    report_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, str]:
    report = await session.get(Report, report_id)
    if report is None or report.run_id != run_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    return {"url": get_evidence_storage().presigned_url(report.storage_key)}
