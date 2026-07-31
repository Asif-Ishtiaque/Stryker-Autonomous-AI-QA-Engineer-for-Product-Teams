# Integration tests

These tests exercise the real FastAPI app (`app.main.app`) over HTTP against
a **real Postgres** database, started as a Docker container via the
[`testcontainers`](https://pypi.org/project/testcontainers/) package
(`tests/integration/conftest.py::postgres_container`). The schema is created
straight from the SQLAlchemy models (`Base.metadata.create_all`), so it's
bit-for-bit what production runs — including `Project.tags`, which is a
genuine Postgres `ARRAY(String)` column.

## Why not SQLite

`Project.tags` is `ARRAY(String)`, a Postgres-only type with no SQLite
equivalent. An in-process `aiosqlite` engine was considered as a fallback,
but it cannot represent this schema without either faking array support (a
lossy approximation of real behavior) or weakening the column in production
code to fit the test — both of which are worse than requiring Postgres.
**Testcontainers Postgres is therefore the only supported path.**

## Requirements to run this suite

- Docker, and a running daemon reachable from wherever `pytest` runs.
- Network access the first time, to pull `postgres:16-alpine`.

If Docker isn't reachable, `postgres_container` calls `pytest.skip(...)` and
the entire suite is skipped with a clear reason — it does not silently fall
back to a weaker substitute.

## What's mocked, and why

Only real *external infra* is replaced, at the network edge (see
`tests/support/stubs.py` and `stub_external_services` /
`stub_celery` in `conftest.py`):

- `get_llm_provider()` → `StubLLMProvider` (inspects `json_schema` to return
  plausible canned JSON for whichever agent is calling)
- `get_embedding_provider()` → `StubEmbeddingProvider` (fixed-length zero vectors)
- `get_chroma_client()` → `StubChromaClient` (in-memory)
- `get_evidence_storage()` → `InMemoryEvidenceStorage` (in-memory dict instead of MinIO)
- `run_requirement_task.delay` / `ingest_knowledge_source_task.delay` →
  `MagicMock` (route-level tests only assert `.delay` was called with the
  right args — they don't execute the task)

Everything else — routing, auth, request/response validation, the ORM
models, the repository layer, and (in `test_run_pipeline.py`) the LangGraph
run graph itself — is real.

`test_run_pipeline.py` is the one test that drives
`app.execution.tasks._run_requirement_async` directly (bypassing Celery,
which isn't running in tests) with a mocked LLM **and** a mocked Executor
(`FakeSuccessExecutor`), to prove the full pipeline wiring and DB persistence
without needing a real browser. The Playwright/browser-execution path itself
is covered for real in `tests/e2e/`.
