# Deployment

## Local development via Docker Compose

The whole stack — Postgres, Redis, ChromaDB, MinIO, OpenSearch, Ollama, OTel collector, Prometheus, Grafana, the FastAPI backend, the Celery worker, and the Next.js frontend — is defined in the root `docker-compose.yml`.

```bash
cp .env.example .env
# generate JWT_SECRET and CREDENTIAL_ENCRYPTION_KEY (see below) and paste into .env
docker compose --profile cpu up --build
```

### CPU vs. GPU profile

Ollama is defined twice under mutually exclusive Compose profiles, both listening on `11434`:

| Service | Profile | Use when |
|---|---|---|
| `ollama-cpu` | `cpu` | No NVIDIA GPU available (default recommendation, works everywhere) |
| `ollama` | `gpu` | An NVIDIA GPU is available — the service requests `driver: nvidia`, `capabilities: [gpu]` |

Run one or the other, never both:

```bash
docker compose --profile cpu up --build   # CPU inference
docker compose --profile gpu up --build   # GPU inference
```

`make up` runs the CPU profile. The `backend` and `worker` services hardcode `LLM_BASE_URL: http://ollama-cpu:11434/v1` in `docker-compose.yml` — if you switch to the `gpu` profile, override `LLM_BASE_URL` to `http://ollama:11434/v1` (both containers listen on the same port, so only the hostname changes).

After the stack is up, pull a model into whichever Ollama container you're running:

```bash
make seed-model   # docker compose exec ollama-cpu ollama pull llama3.1
```

### Makefile targets

| Target | Command | Purpose |
|---|---|---|
| `make up` | `docker compose --profile cpu up --build` | Start the full stack (CPU profile) |
| `make down` | `docker compose down` | Stop everything |
| `make logs` | `docker compose logs -f backend worker` | Tail backend + worker logs |
| `make migrate` | `docker compose exec backend alembic upgrade head` | Apply migrations manually |
| `make revision m="..."` | `docker compose exec backend alembic revision --autogenerate -m "$(m)"` | Generate a new migration from model changes |
| `make seed-model` | `docker compose exec ollama-cpu ollama pull llama3.1` | Pull the default local model |
| `make backend-shell` / `make worker-shell` | `docker compose exec backend|worker bash` | Shell into a running container |
| `make fmt` | `cd backend && ruff format . && ruff check --fix .` | Format + autofix |
| `make lint` | `cd backend && ruff check . && mypy app` | Lint + type-check |
| `make test` | `cd backend && pytest` | Run the test suite |

The `backend` container already runs `alembic upgrade head` automatically before starting `uvicorn` (see its `command:` in `docker-compose.yml`), so a fresh `docker compose up` migrates the database on its own — `make migrate` is for applying new migrations to an already-running stack without a full restart.

## Environment variables

Every variable below is defined in `backend/app/core/config.py::Settings` and read from the process environment (via `pydantic-settings`, `.env` file support enabled). Nothing in application code reads an environment variable directly outside this file — if you need a new external dependency, add it here, not with `os.environ.get(...)` scattered around.

Two files exist at different scopes:
- **Root `.env.example`** — the small set of cross-cutting secrets/config actually meant to be edited per-deployment (copy to `.env`, used by `docker compose up`).
- **`Settings` in `backend/app/core/config.py`** — the full list, including service-to-service hostnames that `docker-compose.yml` already overrides for you inside the Compose network. You only need to override these yourself for local (non-Docker) development or a non-Compose deployment.

| Variable | Default | Purpose |
|---|---|---|
| `APP_NAME` | `Stryker` | Display name |
| `ENVIRONMENT` | `development` | `development` \| `staging` \| `production` |
| `API_PREFIX` | `/api/v1` | Prefix applied to every router except `/healthz` and `/metrics` |
| `DEBUG` | `true` | Verbose logging |
| `FRONTEND_URL` | `http://localhost:3000` | CORS allow-origin |
| `JWT_SECRET` | *(required, no default)* | Signs access/refresh JWTs |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `14` | Refresh token TTL |
| `CREDENTIAL_ENCRYPTION_KEY` | *(required, no default)* | 32-byte urlsafe-base64 Fernet key encrypting AUT credentials at rest |
| `DATABASE_URL` | `postgresql+asyncpg://stryker:stryker@postgres:5432/stryker` | Postgres connection string (async driver) |
| `REDIS_URL` | `redis://redis:6379/0` | Pub/sub + general cache DB |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` | Celery task broker |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/2` | Celery result backend |
| `CHROMA_HOST` | `chroma` | ChromaDB host |
| `CHROMA_PORT` | `8000` | ChromaDB port (container-internal; mapped to `8001` on the host) |
| `CHROMA_COLLECTION_PREFIX` | `stryker_kb` | Prefix for per-project collection names |
| `MINIO_ENDPOINT` | `minio:9000` | MinIO endpoint |
| `MINIO_ACCESS_KEY` | `stryker` | MinIO access key |
| `MINIO_SECRET_KEY` | `stryker-secret` | MinIO secret key |
| `MINIO_SECURE` | `false` | Use HTTPS to talk to MinIO |
| `MINIO_EVIDENCE_BUCKET` | `stryker-evidence` | Bucket for uploads, evidence, and reports |
| `OPENSEARCH_URL` | `http://opensearch:9200` | OpenSearch endpoint — **provisioned, not yet indexed into (see ARCHITECTURE.md known gaps)** |
| `OPENSEARCH_INDEX_PREFIX` | `stryker-runs` | Reserved index prefix for when indexing is implemented |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4317` | OTLP gRPC trace exporter target |
| `ENABLE_TRACING` | `true` | Disable to skip all OTel instrumentation in local dev |
| `LLM_PROVIDER` | `ollama` | `ollama` \| `vllm` \| `lmstudio` \| `openai_compatible` — all four resolve to the same `OpenAICompatibleProvider` client |
| `LLM_MODEL` | `llama3.1` | Model name/tag passed to the chat-completions call |
| `LLM_BASE_URL` | `http://ollama:11434/v1` | Base URL of the OpenAI-compatible endpoint |
| `LLM_API_KEY` | `not-needed` | API key, if the endpoint requires one |
| `LLM_TEMPERATURE` | `0.1` | Default sampling temperature for agent calls |
| `LLM_REQUEST_TIMEOUT_SECONDS` | `120` | Per-request timeout |
| `EMBEDDING_MODEL` | `BAAI/bge-small-en-v1.5` | Any `sentence-transformers`-compatible checkpoint |
| `EMBEDDING_DEVICE` | `cpu` | `cpu` or `cuda` |
| `BROWSER_POOL_SIZE` | `4` | Warm Chromium instances kept alive by `BrowserPool` |
| `BROWSER_HEADLESS` | `true` | Run Chromium headless |
| `MAX_PLAN_RETRIES` | `2` | Bound on the `executor → bump_retry → planner` replan loop |
| `DEFAULT_STEP_TIMEOUT_MS` | `15000` | Default per-step timeout used by executors |
| `MAX_CONCURRENT_RUNS` | `50` | Soft cap referenced by the execution engine for concurrency planning |

Generate the two required secrets (`JWT_SECRET`, `CREDENTIAL_ENCRYPTION_KEY`) with the one-liners already in `.env.example`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## Running Alembic migrations

```bash
make migrate                       # docker compose exec backend alembic upgrade head
make revision m="add foo column"   # docker compose exec backend alembic revision --autogenerate -m "add foo column"
```

`backend/alembic/env.py` imports `app.db.models` (via `from app.db.models import *`) so `Base.metadata` — and therefore autogenerate — sees every model without needing to list them by hand. As of this writing the `alembic/versions/` directory is empty: the schema is created by whatever migration(s) you generate from the current models (`make revision m="initial schema"`) before the first `alembic upgrade head`. Running the stack via `docker compose up` still works because the `backend` container runs `alembic upgrade head` on every start — generate that first migration before you expect a working database.

Outside Docker (running Alembic against a local Postgres):

```bash
cd backend
DATABASE_URL=postgresql+asyncpg://stryker:stryker@localhost:5432/stryker alembic upgrade head
```

## Pointing at an external LLM provider instead of local Ollama

Set three variables (root `.env`, or however you inject environment into `backend`/`worker` in your deployment):

```bash
LLM_PROVIDER=openai_compatible
LLM_BASE_URL=https://your-endpoint.example.com/v1
LLM_API_KEY=sk-...
LLM_MODEL=your-model-name
```

Because `ollama`, `vllm`, `lmstudio`, and `openai_compatible` all resolve to the same `OpenAICompatibleProvider` (`app/llm/registry.py::build_llm_provider`), there is no code difference between "local Ollama" and "hosted OpenAI-compatible API" — only `LLM_BASE_URL`/`LLM_API_KEY`/`LLM_MODEL` change. You do not need the `ollama`/`ollama-cpu` Compose service running at all if you set this — you can remove it from the `docker compose up` invocation, or leave it defined but simply unused.

Embeddings (`EMBEDDING_MODEL`/`EMBEDDING_DEVICE`) are independent of `LLM_PROVIDER` — they always run locally via `sentence-transformers`, so switching the reasoning LLM to a hosted endpoint does not send your knowledge-base documents anywhere.

## Production considerations

This repository ships a Docker Compose stack suitable for a single-host deployment or local development. Before running Stryker against real production application traffic, consider:

- **Secrets management.** `.env` is a plaintext file by design for local dev. In production, inject `JWT_SECRET`, `CREDENTIAL_ENCRYPTION_KEY`, `LLM_API_KEY`, and the Postgres/MinIO credentials via your platform's secret manager (e.g. Vault, AWS Secrets Manager, Kubernetes Secrets) rather than a committed or long-lived `.env` file. Rotate `CREDENTIAL_ENCRYPTION_KEY` carefully — rotating it without a re-encryption migration makes every existing `CredentialProfile` row undecryptable.
- **TLS termination.** Nothing in `docker-compose.yml` terminates TLS. Put a reverse proxy (nginx, Caddy, Traefik, or a cloud load balancer) in front of `backend:8000` and `frontend:3000`, and make sure the WebSocket upgrade (`/api/v1/ws/runs/{run_id}`) is proxied correctly (`Upgrade`/`Connection` headers, no aggressive idle timeout — long runs hold the socket open for the duration of the run).
- **Scaling the Celery worker pool.** `Dockerfile.worker`'s default command runs `celery worker --concurrency=4`. Each concurrent task can drive one browser context at a time via the shared `BrowserPool`; size `BROWSER_POOL_SIZE` (`app/execution/browser_pool.py`) to comfortably cover worker concurrency across however many worker replicas you run — a pool that's smaller than total concurrent demand means tasks queue waiting for a browser, not extra parallelism. Scale worker replicas horizontally (multiple `worker` containers/pods pointed at the same Redis broker) rather than only raising `--concurrency` on one host, since each worker process also needs enough memory/CPU for however many live Chromium processes its own pool holds.
- **`MAX_CONCURRENT_RUNS`.** This setting is a soft cap referenced by the execution engine; make sure it's consistent with your actual worker concurrency × replica count, not set independently of it.
- **Backing up Postgres and MinIO.** Postgres holds every project, requirement, run, step, and (encrypted) credential — back it up like any relational system of record (`pg_dump`/WAL archiving/managed-Postgres snapshots). MinIO holds every screenshot, DOM snapshot, raw knowledge upload, and rendered report — back it up as object storage (versioning + cross-region replication if you're running it yourself, or use a managed S3-compatible service with its own backup story). The two are linked by `storage_key` strings in Postgres rows; losing MinIO without losing Postgres leaves you with metadata pointing at nothing, and vice versa — back up both together or plan for that inconsistency.
- **ChromaDB persistence.** Knowledge embeddings live in the `chroma-data` volume. It's regenerable from the original uploads in MinIO (re-run ingestion), but that costs re-embedding time — decide whether that's an acceptable recovery path or whether you want to back up the volume directly.

## Kubernetes

Kubernetes manifests are **not included in this repository**. The Docker Compose file is the only deployment topology shipped today; treat production Kubernetes manifests (Deployments, StatefulSets for Postgres/Redis/Chroma/MinIO or externalizing them to managed services, an Ingress with WebSocket support, HPA for the worker) as a roadmap item, not something to expect to find here yet.
