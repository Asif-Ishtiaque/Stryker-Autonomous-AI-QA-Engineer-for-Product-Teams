from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.rag.parsers  # noqa: F401 — populates the parser registry
from app.agents.executors import get_executor_class  # noqa: F401 — populates the executor registry
from app.api.routers import auth, chat, credentials, health, knowledge, projects, reports, requirements, runs, ws
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.core.telemetry import configure_telemetry
from app.execution.browser_pool import get_browser_pool

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.debug)
    logger.info("stryker.starting", environment=settings.environment)
    await get_browser_pool().start()
    yield
    await get_browser_pool().stop()
    logger.info("stryker.stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Stryker API",
        description="The Autonomous AI QA Engineer — backend service.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    configure_telemetry(app, settings)

    prefix = settings.api_prefix
    app.include_router(health.router)
    app.include_router(auth.router, prefix=prefix)
    app.include_router(projects.router, prefix=prefix)
    app.include_router(credentials.router, prefix=prefix)
    app.include_router(knowledge.router, prefix=prefix)
    app.include_router(requirements.router, prefix=prefix)
    app.include_router(runs.router, prefix=prefix)
    app.include_router(reports.router, prefix=prefix)
    app.include_router(chat.router, prefix=prefix)
    app.include_router(ws.router, prefix=prefix)

    return app


app = create_app()
