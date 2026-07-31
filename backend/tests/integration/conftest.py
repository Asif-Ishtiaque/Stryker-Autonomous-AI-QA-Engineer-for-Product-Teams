"""Integration test fixtures.

These tests exercise the real FastAPI app (app.main.app) end-to-end at the
HTTP layer against a REAL Postgres database, started as a Docker container
via the `testcontainers` package. Nothing about the database is faked or
simplified — Project.tags is a genuine Postgres ARRAY column and the schema
is created straight from the SQLAlchemy models (Base.metadata.create_all),
so these tests run against the same shapes production does.

Everything that talks to infra Stryker can't reasonably spin up in a test
process (an LLM, a local embeddings model download, Chroma, MinIO, Celery/
Redis) is replaced at the network edge with a stand-in from
tests/support/stubs.py — see stub_external_services below. Playwright/browser
execution is NOT touched here; that's covered separately in tests/e2e.

If Docker isn't reachable in the environment running these tests, the whole
suite is skipped (see `postgres_container`) rather than silently falling
back to a weaker substitute — a SQLite engine cannot represent
Project.tags (ARRAY(String), Postgres-only), and weakening that column to
make SQLite work would be changing production code to fit a test shortcut.
"""
from __future__ import annotations

import os

os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("CREDENTIAL_ENCRYPTION_KEY", "h2iPuG1_CJtLhpeDDvytAs9k0Gzc023YYVYEkeLEZ5U=")
os.environ.setdefault("ENABLE_TRACING", "false")

import asyncio
import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from tests.support.stubs import InMemoryEvidenceStorage, StubChromaClient, StubEmbeddingProvider, StubLLMProvider

_ALL_TABLES = [
    "evidence",
    "steps",
    "reports",
    "runs",
    "requirements",
    "knowledge_sources",
    "credential_profiles",
    "projects",
    "users",
]


@pytest.fixture(scope="session")
def postgres_container():
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip("testcontainers is not installed — integration tests require a real Postgres.")

    try:
        container = PostgresContainer("postgres:16-alpine", driver="asyncpg")
        container.start()
    except Exception as exc:  # noqa: BLE001 — any Docker/daemon failure means "skip", not "error"
        pytest.skip(f"Docker/Postgres testcontainer not available in this environment: {exc}")
        return

    yield container
    container.stop()


@pytest.fixture(scope="session")
def database_url(postgres_container) -> str:
    return postgres_container.get_connection_url()


@pytest.fixture(scope="session")
def _schema_ready(database_url: str) -> None:
    """Creates the real schema (straight from the ORM models) once per test session.

    Retries a few times: the official postgres image restarts itself once internally after initdb
    bootstrap before it's truly ready to serve the exposed TCP port, and testcontainers' readiness
    probe (an in-container `psql`) can return before that settles — observed here as create_all()
    completing without error against a connection that doesn't end up reflecting reality moments
    later (a subsequent TRUNCATE reports the table doesn't exist). Verifying table count after
    create_all and retrying closes that race without weakening what's actually being tested.
    """
    from sqlalchemy import text

    from app.db.base import Base

    expected_tables = set(Base.metadata.tables.keys())

    async def _create_and_verify() -> bool:
        engine = create_async_engine(database_url)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async with engine.connect() as conn:
                result = await conn.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                )
                existing = {row[0] for row in result.fetchall()}
            return expected_tables <= existing
        finally:
            await engine.dispose()

    async def _run_with_retries() -> None:
        last_exc: Exception | None = None
        for attempt in range(5):
            try:
                if await _create_and_verify():
                    return
            except Exception as exc:  # noqa: BLE001 — transient startup races only, retried below
                last_exc = exc
            await asyncio.sleep(1)
        if last_exc:
            raise last_exc
        raise RuntimeError("Schema tables did not appear after retrying create_all against Postgres.")

    asyncio.run(_run_with_retries())


@pytest_asyncio.fixture
async def test_engine(database_url: str, _schema_ready: None):
    # NullPool + a fresh engine per test function: asyncpg connections are bound to the event
    # loop that created them, and pytest-asyncio uses a fresh loop per test by default, so engines
    # (and their pooled connections) must not be shared across test functions.
    engine = create_async_engine(database_url, poolclass=NullPool)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_sessionmaker(test_engine):
    return async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)


@pytest_asyncio.fixture
async def db_session(db_sessionmaker) -> AsyncIterator[AsyncSession]:
    """A standalone session tests can use to set up/inspect rows directly, independent of
    whatever session a given HTTP request used."""
    async with db_sessionmaker() as session:
        yield session


@pytest_asyncio.fixture(autouse=True)
async def _override_db_dependencies(db_sessionmaker, monkeypatch):
    from app.core.di import get_db
    from app.db.session import get_session
    from app.main import app

    async def _override():
        async with db_sessionmaker() as session:
            yield session

    app.dependency_overrides[get_db] = _override
    app.dependency_overrides[get_session] = _override

    # app.execution.tasks._run_requirement_async opens its own session via AsyncSessionLocal
    # directly (Celery tasks run outside FastAPI's DI), so point that at the test DB too — used
    # by the one test that drives the pipeline task function directly.
    monkeypatch.setattr("app.execution.tasks.AsyncSessionLocal", db_sessionmaker)

    yield

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_session, None)


@pytest_asyncio.fixture(autouse=True)
async def _truncate_tables(test_engine):
    yield
    async with test_engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE TABLE {', '.join(_ALL_TABLES)} RESTART IDENTITY CASCADE"))


@pytest.fixture(autouse=True)
def stub_external_services(monkeypatch):
    """Patches every real-infra call site at the network edge: LLM provider, embeddings
    provider, Chroma client, and MinIO-backed evidence storage. Each is patched at every module
    that imported it via `from x import y` (patching only the defining module would not affect
    names already bound elsewhere)."""
    llm = StubLLMProvider()
    embeddings = StubEmbeddingProvider()
    chroma = StubChromaClient()
    storage = InMemoryEvidenceStorage()

    for target in (
        "app.api.routers.requirements.get_llm_provider",
        "app.api.routers.chat.get_llm_provider",
        "app.execution.tasks.get_llm_provider",
    ):
        monkeypatch.setattr(target, lambda: llm)

    for target in (
        "app.rag.retriever.get_embedding_provider",
        "app.rag.ingestion.get_embedding_provider",
    ):
        monkeypatch.setattr(target, lambda: embeddings)

    for target in (
        "app.api.routers.projects.get_chroma_client",
        "app.api.routers.knowledge.get_chroma_client",
        "app.rag.retriever.get_chroma_client",
        "app.rag.ingestion.get_chroma_client",
    ):
        monkeypatch.setattr(target, lambda: chroma)

    for target in (
        "app.api.routers.knowledge.get_evidence_storage",
        "app.api.routers.runs.get_evidence_storage",
        "app.api.routers.reports.get_evidence_storage",
        "app.execution.tasks.get_evidence_storage",
        "app.evidence.capture.get_evidence_storage",
    ):
        monkeypatch.setattr(target, lambda: storage)

    return {"llm": llm, "embeddings": embeddings, "chroma": chroma, "storage": storage}


@pytest.fixture(autouse=True)
def stub_celery(monkeypatch):
    """Celery tasks are never actually run from route-level tests — routes just need to see
    `.delay(...)` get called with the right args. `run_requirement_task` and
    `ingest_knowledge_source_task` are single Task objects shared by reference across every module
    that imported them, so patching the `.delay` attribute on the object itself (rather than on
    any one module's name for it) affects every call site at once."""
    from unittest.mock import MagicMock

    from app.execution.celery_app import celery_app
    from app.execution.tasks import ingest_knowledge_source_task, run_requirement_task

    # create_run() pins the Celery task_id to the run's own id via apply_async(...) (so cancel_run
    # can revoke that exact id later); ingestion just uses plain .delay(...).
    monkeypatch.setattr(run_requirement_task, "apply_async", MagicMock())
    monkeypatch.setattr(ingest_knowledge_source_task, "delay", MagicMock())
    monkeypatch.setattr(celery_app.control, "revoke", MagicMock())

    return {"run_requirement_task": run_requirement_task, "ingest_knowledge_source_task": ingest_knowledge_source_task}


@pytest_asyncio.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    from app.main import app

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def _register(client: httpx.AsyncClient, email: str, name: str = "Test User", password: str = "s3cret-pass") -> dict:
    resp = await client.post("/api/v1/auth/register", json={"email": email, "name": name, "password": password})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _login(client: httpx.AsyncClient, email: str, password: str = "s3cret-pass") -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest_asyncio.fixture
async def owner_headers(client: httpx.AsyncClient) -> dict[str, str]:
    """Registers the FIRST user in a clean DB, who becomes 'owner' per app/api/routers/auth.py."""
    email = f"owner-{uuid.uuid4().hex[:8]}@example.com"
    await _register(client, email)
    token = await _login(client, email)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def project_id(client: httpx.AsyncClient, owner_headers: dict[str, str]) -> uuid.UUID:
    resp = await client.post(
        "/api/v1/projects",
        json={
            "name": "Invoicing",
            "description": "Core invoicing flows",
            "platform": "web",
            "base_url": "https://app.example.com",
            "tags": ["billing", "core"],
        },
        headers=owner_headers,
    )
    assert resp.status_code == 201, resp.text
    return uuid.UUID(resp.json()["id"])
