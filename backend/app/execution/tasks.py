"""Celery tasks — the boundary where async agent/executor code (which needs
an event loop) is driven from Celery's synchronous task model via
`asyncio.run`. Two tasks: one runs a Requirement end-to-end, the other
indexes an uploaded knowledge document.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import uuid

from sqlalchemy import select

from app.agents.graph import build_run_graph
from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import get_cipher
from app.db.models.credential import CredentialProfile
from app.db.models.knowledge import KnowledgeSource
from app.db.models.project import Project
from app.db.models.requirement import Requirement
from app.db.models.report import Report
from app.db.models.run import Evidence, Run, Step
from app.db.session import AsyncSessionLocal, dispose_stale_pool
from app.domain.enums import KnowledgeIndexStatus, ReportFormat, RunStatus, StepStatus
from app.evidence.storage import get_evidence_storage
from app.execution.celery_app import celery_app
from app.execution.pubsub import publish_sync
from app.llm.registry import get_llm_provider
from app.rag.ingestion import ingest_document
from app.rag.retriever import context_snippets_for_requirement

logger = get_logger(__name__)


@celery_app.task(name="stryker.run_requirement")
def run_requirement_task(run_id: str) -> None:
    asyncio.run(_run_requirement_async(uuid.UUID(run_id)))


async def _run_requirement_async(run_id: uuid.UUID) -> None:
    await dispose_stale_pool()
    async with AsyncSessionLocal() as session:
        run = await session.get(Run, run_id)
        if run is None:
            logger.error("run_task.missing_run", run_id=str(run_id))
            return

        requirement = await session.get(Requirement, run.requirement_id)
        project = await session.get(Project, run.project_id)
        credential_dict: dict | None = None
        if requirement and requirement.credential_profile_id:
            profile = await session.get(CredentialProfile, requirement.credential_profile_id)
            if profile:
                import json as _json

                cipher = get_cipher()
                credential_dict = {
                    "username": cipher.decrypt(profile.encrypted_username) if profile.encrypted_username else None,
                    "password": cipher.decrypt(profile.encrypted_password) if profile.encrypted_password else None,
                    "api_token": cipher.decrypt(profile.encrypted_api_token) if profile.encrypted_api_token else None,
                    "bearer_token": cipher.decrypt(profile.encrypted_bearer_token) if profile.encrypted_bearer_token else None,
                    "cookies": _json.loads(cipher.decrypt(profile.encrypted_cookies)) if profile.encrypted_cookies else None,
                    "headers": _json.loads(cipher.decrypt(profile.encrypted_headers)) if profile.encrypted_headers else None,
                    "env_vars": _json.loads(cipher.decrypt(profile.encrypted_env_vars)) if profile.encrypted_env_vars else None,
                }

        run.status = RunStatus.PLANNING
        run.started_at = dt.datetime.now(dt.timezone.utc)
        await session.commit()
        publish_sync(run_id, {"run_id": str(run_id), "run_status": "planning", "message": "Starting run"})

        async def on_event(event: dict) -> None:
            enriched = dict(event)
            if event.get("step_status") in ("passed", "failed") and event.get("sequence") is not None:
                step_id, evidence_summaries = await _persist_step_result(session, run, event)
                enriched["step_id"] = str(step_id)
                enriched["evidence"] = evidence_summaries
                # The raw payload is only needed to persist the row above — once it's in
                # the database the frontend fetches it the normal way (REST + presigned
                # URLs, keyed by the evidence ids just attached), so drop the heavy fields
                # rather than pushing full screenshots/DOM/HTML over the WS channel too.
                enriched.pop("evidence_refs", None)
                enriched.pop("result", None)
                enriched.pop("parameters", None)
            publish_sync(run_id, {"run_id": str(run_id), **enriched})

        # Everything from here through graph execution is wrapped in one broad try/except.
        # A run must NEVER be left stuck at an intermediate status (e.g. "planning") because
        # some step before the graph itself — knowledge retrieval, credential handling, LLM
        # provider construction — threw. Any failure here is still a real, reportable outcome
        # for the user, so it's persisted as ERRORED and published, exactly like a graph-level
        # crash below.
        try:
            knowledge_context = context_snippets_for_requirement(project.id, requirement.text) if project else []

            initial_state = {
                "run_id": str(run_id),
                "project_id": str(project.id),
                "platform": str(project.platform),
                "base_url": project.base_url,
                "requirement_text": requirement.text,
                "knowledge_context": knowledge_context,
                "credential": credential_dict,
                "plan_retry_count": 0,
            }

            graph = build_run_graph(get_llm_provider(), on_event)
            final_state = await graph.ainvoke(initial_state, config={"recursion_limit": 50})
        except Exception as exc:  # noqa: BLE001 — persisted as an errored run, not swallowed
            logger.error("run_task.crashed", run_id=str(run_id), error=str(exc))
            run.status = RunStatus.ERRORED
            run.error_message = str(exc)
            run.finished_at = dt.datetime.now(dt.timezone.utc)
            await session.commit()
            publish_sync(run_id, {"run_id": str(run_id), "run_status": "errored", "message": str(exc)})
            return

        await _persist_final_state(session, run, final_state)
        publish_sync(
            run_id,
            {
                "run_id": str(run_id),
                "run_status": final_state.get("final_status", "errored"),
                "confidence_score": final_state.get("confidence_score"),
                "message": "Run complete",
            },
        )


async def _persist_step_result(session, run: Run, event: dict) -> tuple[uuid.UUID, list[dict]]:
    """Writes one step's Step+Evidence rows the moment it completes, instead of
    waiting for the whole run to finish (see _persist_final_state, which used
    to do this in bulk at the end). This is what lets Mission Control's live
    Evidence/Console/Network panels show real data *during* execution — the
    frontend fetches evidence via the normal REST/presigned-URL path using the
    ids this returns, exactly as it does for a finished run.
    """
    step = Step(
        run_id=run.id,
        sequence=event["sequence"],
        name=event.get("name") or f"Step {event['sequence']}",
        action_type=event.get("action_type") or "unknown",
        parameters=event.get("parameters") or {},
        status=StepStatus.PASSED if event["step_status"] == "passed" else StepStatus.FAILED,
        result=event.get("result") or {},
        error_message=event.get("error_message"),
        started_at=run.started_at,
        finished_at=dt.datetime.now(dt.timezone.utc),
    )
    session.add(step)
    await session.flush()

    evidence_summaries: list[dict] = []
    for ref in event.get("evidence_refs") or []:
        evidence = Evidence(
            step_id=step.id,
            evidence_type=ref["evidence_type"],
            storage_key=ref.get("storage_key"),
            inline_data=ref.get("inline_data"),
            content_type=ref.get("content_type"),
        )
        session.add(evidence)
        await session.flush()
        evidence_summaries.append({"id": str(evidence.id), "evidence_type": evidence.evidence_type})

    await session.commit()
    return step.id, evidence_summaries


async def _persist_final_state(session, run: Run, state: dict) -> None:
    status_map = {"passed": RunStatus.PASSED, "failed": RunStatus.FAILED, "errored": RunStatus.ERRORED}
    run.status = status_map.get(state.get("final_status", "errored"), RunStatus.ERRORED)
    run.plan = {"steps": state.get("plan", [])}
    run.validation_checklist = {"findings": state.get("validation_findings", [])}
    run.confidence_score = state.get("confidence_score")
    run.severity = state.get("severity")
    run.root_cause_hypothesis = state.get("root_cause_hypothesis")
    run.root_cause_analysis = state.get("root_cause_analysis")
    run.error_message = state.get("execution_error")
    run.report_markdown = state.get("report_markdown")
    run.finished_at = dt.datetime.now(dt.timezone.utc)
    if run.started_at:
        run.duration_ms = int((run.finished_at - run.started_at).total_seconds() * 1000)

    # Step/Evidence rows for this run were already written incrementally as each
    # step completed — see _persist_step_result, invoked from on_event above.
    storage = get_evidence_storage()

    if state.get("report_markdown"):
        markdown_key = storage.put_bytes(
            f"reports/{run.id}", state["report_markdown"].encode(), "text/markdown", ".md"
        )
        session.add(Report(run_id=run.id, format=ReportFormat.MARKDOWN, storage_key=markdown_key))
    if state.get("report_json"):
        import json as _json

        json_key = storage.put_bytes(
            f"reports/{run.id}", _json.dumps(state["report_json"], default=str).encode(), "application/json", ".json"
        )
        session.add(Report(run_id=run.id, format=ReportFormat.JSON, storage_key=json_key))

    await session.commit()


@celery_app.task(name="stryker.ingest_knowledge_source")
def ingest_knowledge_source_task(knowledge_source_id: str) -> None:
    asyncio.run(_ingest_knowledge_source_async(uuid.UUID(knowledge_source_id)))


async def _ingest_knowledge_source_async(knowledge_source_id: uuid.UUID) -> None:
    await dispose_stale_pool()
    async with AsyncSessionLocal() as session:
        source = await session.get(KnowledgeSource, knowledge_source_id)
        if source is None:
            return

        source.status = KnowledgeIndexStatus.PROCESSING
        await session.commit()

        try:
            raw_bytes = get_evidence_storage().get_bytes(source.storage_key)
            chunk_count = ingest_document(source.project_id, source.id, source.filename, source.source_type, raw_bytes)
            source.status = KnowledgeIndexStatus.INDEXED
            source.chunk_count = chunk_count
        except Exception as exc:  # noqa: BLE001 — recorded on the row, surfaced to the UI
            logger.error("ingestion.failed", source_id=str(knowledge_source_id), error=str(exc))
            source.status = KnowledgeIndexStatus.FAILED
            source.error_message = str(exc)

        await session.commit()
