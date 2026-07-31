"""Per-project AI chat — answers questions like "why did Invoice fail last
week?" by retrieving both the knowledge base (Chroma) and finished Run
reports (Postgres) as context, then asking the LLM to answer grounded in
that evidence rather than free-associating.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.di import get_current_user, get_db
from app.db.models.run import Run
from app.db.models.user import User
from app.llm.base import ChatMessage
from app.llm.registry import get_llm_provider
from app.rag.retriever import semantic_search
from app.schemas.chat import ChatMessageRequest, ChatMessageResponse, ChatSource

router = APIRouter(prefix="/chat", tags=["chat"])

SYSTEM_PROMPT = """You are Stryker's project assistant. Answer the user's question about this
project's QA history using ONLY the provided context (past run reports and knowledge base
excerpts). If the context doesn't contain the answer, say so plainly instead of guessing.
Be concise and specific — cite requirement text or run outcomes where relevant."""


@router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(
    payload: ChatMessageRequest, session: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)
) -> ChatMessageResponse:
    knowledge_hits = semantic_search(payload.project_id, payload.message, top_k=5)

    recent_runs = (
        await session.execute(
            select(Run).where(Run.project_id == payload.project_id).order_by(Run.created_at.desc()).limit(20)
        )
    ).scalars().all()

    run_context = "\n".join(
        f"- Run {r.id} ({r.status}): confidence={r.confidence_score}, severity={r.severity}, "
        f"root_cause={r.root_cause_hypothesis}"
        for r in recent_runs
    )
    knowledge_context = "\n".join(f"- [{h.source_filename}] {h.chunk_text}" for h in knowledge_hits)

    user_prompt = (
        f"Question: {payload.message}\n\n"
        f"Recent runs:\n{run_context or '(no runs yet)'}\n\n"
        f"Knowledge base excerpts:\n{knowledge_context or '(no knowledge sources indexed)'}"
    )

    answer = await get_llm_provider().chat(
        [ChatMessage(role="system", content=SYSTEM_PROMPT), ChatMessage(role="user", content=user_prompt)]
    )

    sources = [
        ChatSource(kind="run", ref_id=r.id, snippet=f"{r.status} — confidence {r.confidence_score}")
        for r in recent_runs[:5]
    ] + [ChatSource(kind="knowledge", ref_id=uuid.uuid4(), snippet=h.chunk_text[:200]) for h in knowledge_hits[:5]]

    return ChatMessageResponse(conversation_id=payload.conversation_id or uuid.uuid4(), answer=answer, sources=sources)
