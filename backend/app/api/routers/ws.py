"""WebSocket endpoint the frontend's live-execution page subscribes to.
Bridges Redis pub/sub (published by the Celery worker) straight through to
the browser — no polling, and the connection closes itself once the run
reaches a terminal status.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routers.ws_auth import authorize_run_websocket
from app.core.di import get_db
from app.execution.pubsub import subscribe

router = APIRouter(tags=["websocket"])

_TERMINAL_STATUSES = {"passed", "failed", "errored", "cancelled"}


@router.websocket("/ws/runs/{run_id}")
async def run_events(websocket: WebSocket, run_id: uuid.UUID, session: AsyncSession = Depends(get_db)) -> None:
    if await authorize_run_websocket(websocket, run_id, session) is None:
        return
    await websocket.accept()
    try:
        async for event in subscribe(run_id):
            await websocket.send_json(event)
            if event.get("run_status") in _TERMINAL_STATUSES:
                break
    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()
