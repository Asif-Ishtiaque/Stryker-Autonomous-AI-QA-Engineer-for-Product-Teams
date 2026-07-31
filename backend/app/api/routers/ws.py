"""WebSocket endpoint the frontend's live-execution page subscribes to.
Bridges Redis pub/sub (published by the Celery worker) straight through to
the browser — no polling, and the connection closes itself once the run
reaches a terminal status.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.execution.pubsub import subscribe

router = APIRouter(tags=["websocket"])

_TERMINAL_STATUSES = {"passed", "failed", "errored", "cancelled"}


@router.websocket("/ws/runs/{run_id}")
async def run_events(websocket: WebSocket, run_id: uuid.UUID) -> None:
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
