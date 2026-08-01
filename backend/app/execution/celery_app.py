from __future__ import annotations

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "stryker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.execution.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=200,
    task_acks_late=True,
    task_time_limit=settings.run_task_time_limit_seconds,
    task_soft_time_limit=max(settings.run_task_time_limit_seconds - 60, 1),
)
