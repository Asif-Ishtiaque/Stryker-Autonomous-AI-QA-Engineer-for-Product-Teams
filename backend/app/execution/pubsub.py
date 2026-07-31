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


def publish_sync(run_id: uuid.UUID, event: dict) -> None:
    """Used from inside Celery tasks, which are synchronous."""
    settings = get_settings()
    client = redis.from_url(settings.redis_url)
    try:
        client.publish(channel_name(run_id), json.dumps(event, default=str))
    finally:
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
