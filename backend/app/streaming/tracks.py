"""A WebRTC video track sourced from JPEG frames relayed over Redis pub/sub
by the Celery worker's CDP screencast (see
app.agents.executors.web.screencast). This is the piece that actually turns
"a run_id" into a live aiortc MediaStreamTrack a browser can render.
"""
from __future__ import annotations

import asyncio
import io
import uuid

import numpy as np
from aiortc.mediastreams import VideoStreamTrack
from av import VideoFrame
from PIL import Image

from app.core.logging import get_logger
from app.execution.pubsub import subscribe_frames

logger = get_logger(__name__)

# Shown while no frame has arrived yet (run not started, or between runs) so the
# peer connection always has something to render instead of stalling negotiation.
_PLACEHOLDER_FRAME = np.zeros((480, 640, 3), dtype=np.uint8)


class RedisFrameTrack(VideoStreamTrack):
    kind = "video"

    def __init__(self, run_id: uuid.UUID) -> None:
        super().__init__()
        self._run_id = run_id
        self._latest = _PLACEHOLDER_FRAME
        self._stopped = False
        self._consume_task = asyncio.ensure_future(self._consume())

    async def _consume(self) -> None:
        try:
            async for jpeg_bytes in subscribe_frames(self._run_id):
                if self._stopped:
                    break
                try:
                    image = Image.open(io.BytesIO(jpeg_bytes)).convert("RGB")
                    self._latest = np.array(image)
                except Exception as exc:  # noqa: BLE001 — keep showing the last good frame
                    logger.warning("frame_track.decode_failed", run_id=str(self._run_id), error=str(exc))
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # noqa: BLE001 — a broken subscription must not crash the track
            logger.warning("frame_track.subscribe_failed", run_id=str(self._run_id), error=str(exc))

    async def recv(self) -> VideoFrame:
        pts, time_base = await self.next_timestamp()
        frame = VideoFrame.from_ndarray(self._latest, format="rgb24")
        frame.pts = pts
        frame.time_base = time_base
        return frame

    def stop(self) -> None:
        self._stopped = True
        if not self._consume_task.done():
            self._consume_task.cancel()
        super().stop()
