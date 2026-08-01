"""Redis pub/sub bridge between the Celery worker (publisher) and the
FastAPI WebSocket endpoint (subscriber). Chosen over having the worker talk
to WebSocket clients directly because the worker and the API process are
different processes/containers — Redis is the one thing both already share.
"""
from __future__ import annotations

import json
import uuid

import redis
import redis.asyncio as aioredis

from app.core.config import get_settings


def channel_name(run_id: uuid.UUID) -> str:
    return f"stryker:run:{run_id}"


def frame_channel_name(run_id: uuid.UUID) -> str:
    """Separate channel from channel_name() because frames are raw JPEG bytes,
    not JSON — mixing them on one channel would mean every step-event
    subscriber has to sniff each message to know how to decode it."""
    return f"stryker:run:{run_id}:frames"


def publish_sync(run_id: uuid.UUID, event: dict) -> None:
    """Used from inside Celery tasks, which are synchronous."""
    settings = get_settings()
    client = redis.from_url(settings.redis_url)
    try:
        client.publish(channel_name(run_id), json.dumps(event, default=str))
    finally:
        client.close()


def publish_frame_sync(run_id: uuid.UUID, jpeg_bytes: bytes, client: "redis.Redis | None" = None) -> None:
    """Used from inside the Celery worker's CDP screencast frame handler
    (app.agents.executors.web.screencast). Accepts an optional long-lived
    client so a whole run's worth of frames (potentially several per second)
    doesn't open a fresh Redis connection for every single frame."""
    settings = get_settings()
    owns_client = client is None
    client = client or redis.from_url(settings.redis_url)
    try:
        client.publish(frame_channel_name(run_id), jpeg_bytes)
    finally:
        if owns_client:
            client.close()


async def subscribe(run_id: uuid.UUID):
    settings = get_settings()
    client = aioredis.from_url(settings.redis_url)
    pubsub = client.pubsub()
    await pubsub.subscribe(channel_name(run_id))
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            yield json.loads(message["data"])
    finally:
        await pubsub.unsubscribe(channel_name(run_id))
        await client.close()


async def subscribe_frames(run_id: uuid.UUID):
    """Yields raw JPEG frame bytes as they're relayed from the worker's CDP
    screencast. Used by the WebRTC video track (app.streaming.tracks)."""
    settings = get_settings()
    client = aioredis.from_url(settings.redis_url)
    pubsub = client.pubsub()
    await pubsub.subscribe(frame_channel_name(run_id))
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            yield message["data"]
    finally:
        await pubsub.unsubscribe(frame_channel_name(run_id))
        await client.close()
