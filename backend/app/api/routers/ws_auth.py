"""Shared auth check for the two WebSocket endpoints that stream a run's live
data (ws.py's step-event feed and stream.py's WebRTC signaling).

Browsers can't attach an `Authorization` header to a WebSocket upgrade
request from plain JS, so — unlike every REST route — the access token has to
travel as a `?token=` query parameter instead of going through the normal
`Depends(get_current_user)` bearer-token flow. This was a known, documented
gap (both endpoints previously accepted any connection with no check at all);
this closes it by requiring a valid token AND that the token's user owns the
run's project, same ownership rule a REST route would apply.
"""
from __future__ import annotations

import uuid

from fastapi import WebSocket
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.models.project import Project
from app.db.models.run import Run
from app.db.models.user import User

_POLICY_VIOLATION = 1008  # standard WS close code for "message violates policy" (used for auth failures)


async def authorize_run_websocket(websocket: WebSocket, run_id: uuid.UUID, session: AsyncSession) -> Run | None:
    """Validates `?token=` and run ownership. Closes the socket and returns
    None on any failure; the caller should return immediately when this
    happens rather than proceeding to `accept()`."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=_POLICY_VIOLATION, reason="Missing token")
        return None

    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("wrong token type")
        user_id = uuid.UUID(payload["sub"])
    except Exception:  # noqa: BLE001 — any decode failure means "not authenticated"
        await websocket.close(code=_POLICY_VIOLATION, reason="Invalid or expired token")
        return None

    user = await session.get(User, user_id)
    if user is None or not user.is_active:
        await websocket.close(code=_POLICY_VIOLATION, reason="Invalid or expired token")
        return None

    run = await session.get(Run, run_id)
    if run is None:
        await websocket.close(code=_POLICY_VIOLATION, reason="Run not found")
        return None

    project = await session.get(Project, run.project_id)
    if project is None or project.owner_id != user.id:
        await websocket.close(code=_POLICY_VIOLATION, reason="Not authorized for this run")
        return None

    return run
