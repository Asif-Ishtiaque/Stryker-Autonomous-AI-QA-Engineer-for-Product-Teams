"""CDP screencast capture — bridges the live Playwright Page (owned by the
Celery worker process) to the Mission Control WebRTC viewer served by the
FastAPI process. The worker has no direct connection to browser clients, so
frames cross that process boundary the same way step events already do:
Redis pub/sub (see app.execution.pubsub), just on a dedicated per-run channel
carrying raw JPEG bytes instead of JSON.
"""
from __future__ import annotations

import asyncio
import base64
import uuid
from collections.abc import Awaitable, Callable

import redis
from playwright.async_api import Page

from app.core.config import get_settings
from app.core.logging import get_logger
from app.execution.pubsub import publish_frame_sync

logger = get_logger(__name__)


async def start_screencast(page: Page, run_id: uuid.UUID) -> Callable[[], Awaitable[None]]:
    """Starts a CDP Page.startScreencast session on `page` and relays every
    frame to Redis for the WebRTC track to pick up. Returns a stop callback
    to invoke from the executor's teardown()."""
    settings = get_settings()
    frame_client = redis.from_url(settings.redis_url)
    cdp = await page.context.new_cdp_session(page)

    def on_frame(event: dict) -> None:
        try:
            data = base64.b64decode(event["data"])
            publish_frame_sync(run_id, data, client=frame_client)
        except Exception as exc:  # noqa: BLE001 — a dropped frame must never kill the run
            logger.warning("screencast.frame_relay_failed", run_id=str(run_id), error=str(exc))
        finally:
            session_id = event.get("sessionId")
            if session_id is not None:
                # CDP pauses sending further frames until each one is acked (its
                # backpressure mechanism) — this callback is synchronous, so the
                # ack is scheduled on the running loop rather than awaited here.
                asyncio.ensure_future(_ack(cdp, session_id))

    cdp.on("Page.screencastFrame", on_frame)
    await cdp.send(
        "Page.startScreencast",
        {
            "format": "jpeg",
            "quality": settings.screencast_quality,
            "maxWidth": settings.screencast_max_width,
            "maxHeight": settings.screencast_max_height,
            "everyNthFrame": settings.screencast_every_nth_frame,
        },
    )

    async def stop() -> None:
        try:
            await cdp.send("Page.stopScreencast")
        except Exception:  # noqa: BLE001 — page/context may already be gone
            pass
        finally:
            frame_client.close()

    return stop


async def _ack(cdp, session_id: int) -> None:
    try:
        await cdp.send("Page.screencastFrameAck", {"sessionId": session_id})
    except Exception:  # noqa: BLE001 — the session may have already ended
        pass
