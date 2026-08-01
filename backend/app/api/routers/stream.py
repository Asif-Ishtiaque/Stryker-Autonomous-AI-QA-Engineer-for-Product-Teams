"""WebRTC signaling endpoint for Mission Control's live-browser panel.

The Celery worker owns the live Playwright Page and has no direct connection
to browser clients; it relays JPEG frames (from CDP Page.startScreencast) to
this process over Redis pub/sub (see app.agents.executors.web.screencast /
app.execution.pubsub). This endpoint's only job is the SDP offer/answer
exchange that turns those frames into a real WebRTC video track for the
browser — everything after negotiation is native browser-side WebRTC, no
polling, no MJPEG-over-HTTP.

Non-trickle ICE: aiortc gathers host candidates synchronously by the time
setLocalDescription() resolves, so the full answer SDP (candidates included)
can go back over this same WebSocket in one message — no separate ICE
candidate exchange needed for the local/LAN deployments this targets.

NOTE (known limitation, phase 1, matches app/api/routers/ws.py): this endpoint
does not authenticate the connection — see the equivalent note there.
"""
from __future__ import annotations

import uuid

from aiortc import RTCConfiguration, RTCIceServer, RTCPeerConnection, RTCSessionDescription
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import get_settings
from app.core.logging import get_logger
from app.streaming.tracks import RedisFrameTrack

logger = get_logger(__name__)
router = APIRouter(tags=["webrtc"])


def _rtc_configuration() -> RTCConfiguration:
    settings = get_settings()
    turn_url = f"turn:{settings.turn_host}:{settings.turn_port}"
    return RTCConfiguration(
        iceServers=[
            RTCIceServer(
                urls=[turn_url], username=settings.turn_username, credential=settings.turn_credential
            )
        ]
    )


@router.websocket("/ws/runs/{run_id}/stream")
async def stream_signaling(websocket: WebSocket, run_id: uuid.UUID) -> None:
    await websocket.accept()
    pc = RTCPeerConnection(configuration=_rtc_configuration())
    track = RedisFrameTrack(run_id)
    pc.addTrack(track)

    @pc.on("connectionstatechange")
    async def _on_state_change() -> None:
        if pc.connectionState in ("failed", "closed", "disconnected"):
            track.stop()
            await pc.close()

    try:
        message = await websocket.receive_json()
        if message.get("type") != "offer" or "sdp" not in message:
            await websocket.close(code=1002)
            return

        await pc.setRemoteDescription(RTCSessionDescription(sdp=message["sdp"], type="offer"))
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        await websocket.send_json({"type": "answer", "sdp": pc.localDescription.sdp})

        # Media flows over the negotiated peer connection itself, not this socket —
        # it's only kept open afterward to detect when the viewer disconnects.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001 — never let a bad offer crash the process
        logger.warning("webrtc_stream.signaling_failed", run_id=str(run_id), error=str(exc))
    finally:
        track.stop()
        await pc.close()
