# API Reference

Base path: every router below is mounted under `API_PREFIX` (default `/api/v1`) in `app/main.py::create_app`, except `/healthz` (mounted at root) and `/metrics` (added by `prometheus-fastapi-instrumentator`, also at root, undocumented in the OpenAPI schema). So e.g. `POST /projects` in the table below is actually `POST /api/v1/projects`.

**Authentication.** Every route except `POST /auth/register`, `POST /auth/login`, and `GET /healthz` requires a bearer JWT: `Authorization: Bearer <access_token>`, obtained from `POST /auth/login`. Enforcement is `app/core/di.py::get_current_user`, a dependency that decodes the token (`app/core/security.py::decode_token`), verifies `type == "access"` (a refresh token cannot be used as a bearer credential), and loads the corresponding active `User`. Route-level RBAC (`require_role(minimum)`, ranking `owner(3) > admin(2) > member(1) > viewer(0)`) exists in `app/core/di.py` but is not currently applied to any route below — every authenticated user can call every endpoint regardless of role; see the RBAC note in `ARCHITECTURE.md`.

All request/response bodies are the Pydantic schemas in `app/schemas/*.py`; field names below match them exactly.

---

## Health

### `GET /healthz`
No auth. No prefix (mounted at root, not under `API_PREFIX`).
Response `200`: `{"status": "ok"}`

---

## Auth — `app/api/routers/auth.py`

### `POST /auth/register`
No auth required.
Request (`RegisterRequest`): `{email: string, name: string, password: string}`
Response `201` (`UserOut`): `{id: uuid, email: string, name: string, role: "owner"|"admin"|"member"|"viewer"}`
Notes: the first user ever registered becomes `owner`; every subsequent registration becomes `member`. `409` if the email is already registered.

### `POST /auth/login`
No auth required.
Request (`LoginRequest`): `{email: string, password: string}`
Response `200` (`TokenResponse`): `{access_token: string, refresh_token: string, token_type: "bearer"}`
Errors: `401` on invalid email/password.

### `GET /auth/me`
Auth required.
Response `200` (`UserOut`): the authenticated user.

---

## Projects — `app/api/routers/projects.py`

### `POST /projects`
Auth required.
Request (`ProjectCreate`): `{name: string, description?: string, platform: "web"|"rest_api"|"graphql"|"mobile"|"desktop", environment?: "production"|"staging"|"qa"|"development", base_url: string, tags?: string[]}`
Response `201` (`ProjectOut`): `{id, name, description, platform, environment, base_url, tags, status: "active"|"archived"|"paused"}`
Notes: `owner_id` is set to the calling user. Only `platform: "web"` has a registered `Executor` today — creating a project with any other platform succeeds, but running a requirement against it fails at run time with `ValueError: No executor registered for platform '...'`.

### `GET /projects`
Auth required. Response `200`: `ProjectOut[]` — every project (no per-user filtering is applied despite `owner_id` existing).

### `GET /projects/{project_id}`
Auth required. Response `200`: `ProjectOut`. `404` if not found.

### `PATCH /projects/{project_id}`
Auth required.
Request (`ProjectUpdate`, all fields optional): `{name?, description?, environment?, base_url?, tags?, status?}`
Response `200`: `ProjectOut`. `404` if not found.

### `DELETE /projects/{project_id}`
Auth required. Response `204`.
Notes: cascades to delete `KnowledgeSource`, `CredentialProfile`, `Requirement`, and `Run` rows (ORM `cascade="all, delete-orphan"`), and separately deletes the project's ChromaDB collection (`get_chroma_client().delete_collection`).

### `GET /projects/{project_id}/stats`
Auth required.
Response `200` (`ProjectStats`): `{requirement_count: int, run_count: int, pass_rate: float, average_duration_ms: float|null, open_bugs: int, average_confidence: float|null}`
Notes: `pass_rate` = passed runs / total runs; `open_bugs` = count of `failed` + `errored` runs; computed live over all runs, not cached (`ProjectRepository.stats`).

---

## Credentials — `app/api/routers/credentials.py`

All routes prefixed `/projects/{project_id}/credentials`.

### `POST /projects/{project_id}/credentials`
Auth required.
Request (`CredentialCreate`): `{label: string, username?: string, password?: string, api_token?: string, bearer_token?: string, cookies?: {[k:string]: string}, headers?: {[k:string]: string}, env_vars?: {[k:string]: string}}`
Response `201` (`CredentialOut`): `{id, project_id, label, has_username: bool, has_password: bool, has_api_token: bool, has_bearer_token: bool, has_cookies: bool, has_headers: bool}`
Notes: every secret field is Fernet-encrypted server-side (`get_cipher().encrypt(...)`) before the row is written; `cookies`/`headers`/`env_vars` are JSON-serialized then encrypted. Decrypted values are **never** returned by any endpoint — only booleans indicating presence.

### `GET /projects/{project_id}/credentials`
Auth required. Response `200`: `CredentialOut[]` for the project.

### `DELETE /projects/{project_id}/credentials/{credential_id}`
Auth required. Response `204`. `404` if the credential doesn't exist or belongs to a different project.

---

## Knowledge — `app/api/routers/knowledge.py`

All routes prefixed `/projects/{project_id}/knowledge`.

### `POST /projects/{project_id}/knowledge/upload`
Auth required. `multipart/form-data`, field `file`.
Response `201` (`KnowledgeSourceOut`): `{id, project_id, filename, source_type, status: "pending"|"processing"|"indexed"|"failed", chunk_count: int, error_message: string|null}`
Notes: source type is inferred from the file extension (`_EXTENSION_MAP`: `.md`/`.markdown`→markdown, `.pdf`→pdf, `.docx`→docx, `.txt`→txt, `.csv`→csv, `.png`/`.jpg`/`.jpeg`→image, `.sql`→sql, `.json`→openapi, `.yaml`/`.yml`→swagger). `400` for any other extension — Postman collections and screenshots have registered parsers but no upload-extension mapping today, so they can't be uploaded through this endpoint despite being ingestible in principle. The raw file is stored in MinIO immediately and the response returns before indexing finishes; `ingest_knowledge_source_task.delay(...)` runs the parse→chunk→embed pipeline asynchronously — poll `GET /projects/{project_id}/knowledge` and watch `status` to know when it's `indexed` (or `failed`, with `error_message` set).

### `GET /projects/{project_id}/knowledge`
Auth required. Response `200`: `KnowledgeSourceOut[]` for the project.

### `DELETE /projects/{project_id}/knowledge/{source_id}`
Auth required. Response `204`. `404` if not found or belongs to a different project. Notes: deletes the DB row only — does not currently remove the corresponding vectors from the project's Chroma collection or the raw object from MinIO.

### `POST /projects/{project_id}/knowledge/search`
Auth required.
Request (`SemanticSearchRequest`): `{query: string, top_k?: int = 8}`
Response `200`: `SemanticSearchResult[]` — `{source_filename: string, chunk_text: string, score: float, metadata: object}`. `score = 1 - distance` (cosine distance from Chroma). Returns `[]` if the project's collection is empty rather than erroring.

---

## Requirements — `app/api/routers/requirements.py`

All routes prefixed `/projects/{project_id}/requirements`.

### `POST /projects/{project_id}/requirements`
Auth required.
Request (`RequirementCreate`): `{text: string, credential_profile_id?: uuid}`
Response `201` (`RequirementOut`): `{id, project_id, text, credential_profile_id, ai_analysis: RequirementAnalysis|null}`
Notes: `ai_analysis` is `null` until `.../analyze` is called (or a full run has executed the RequirementAgent).

### `GET /projects/{project_id}/requirements`
Auth required. Response `200`: `RequirementOut[]` for the project.

### `GET /projects/{project_id}/requirements/{requirement_id}`
Auth required. Response `200`: `RequirementOut`. `404` if not found or wrong project.

### `POST /projects/{project_id}/requirements/{requirement_id}/analyze`
Auth required.
Response `200` (`RequirementAnalysis`): `{understood_intent: string, expected_outcomes: string[], inferred_validations: string[], identified_risks: string[], predicted_edge_cases: string[], confidence: float}`
Notes: runs **only** the `RequirementAgent` node (not the full graph) — a single fast LLM call (the docstring calls out "<5s") so the UI can preview the AI's understanding of a requirement before the user commits to a full Run. Persists the result onto `Requirement.ai_analysis`. Uses `context_snippets_for_requirement` for RAG context, same as a full run would.

---

## Runs — `app/api/routers/runs.py`

All routes prefixed `/projects/{project_id}/runs`.

### `POST /projects/{project_id}/runs`
Auth required.
Request (`RunCreate`): `{requirement_id: uuid}`
Response `201` (`RunOut`): see shape below. `404` if the requirement doesn't exist or belongs to a different project.
Notes: creates the `Run` row with `status: "queued"` and immediately enqueues `run_requirement_task.delay(str(run.id))` — the response returns before the LangGraph pipeline starts. Subscribe to the WebSocket (below) or poll `GET .../runs/{run_id}` to track progress.

### `GET /projects/{project_id}/runs`
Auth required. Response `200`: `RunOut[]`, most recent first (`order_by(Run.created_at.desc())`).

### `GET /projects/{project_id}/runs/{run_id}`
Auth required.
Response `200` (`RunOut`): `{id, project_id, requirement_id, status: "queued"|"planning"|"running"|"retrying"|"validating"|"passed"|"failed"|"errored"|"cancelled", plan: object|null, validation_checklist: object|null, confidence_score: float|null, severity: string|null, root_cause_hypothesis: string|null, error_message: string|null, report_markdown: string|null, started_at, finished_at, duration_ms: int|null, steps: StepOut[]}`
where `StepOut` = `{id, sequence, name, action_type, parameters: object, status: "waiting"|"running"|"retrying"|"passed"|"failed"|"skipped", retry_count, started_at, finished_at, result: object|null, error_message: string|null, evidence: EvidenceOut[]}`
and `EvidenceOut` = `{id, evidence_type, storage_key: string|null, inline_data: object|null, content_type: string|null}`.
`404` if not found or wrong project. Steps are eager-loaded with their evidence (`RunRepository.get_with_steps`, `selectinload`).

### `POST /projects/{project_id}/runs/{run_id}/cancel`
Auth required.
Response `200`: `RunOut`. `409` if the run is already in a terminal state (`passed`/`failed`/`errored`/`cancelled`).
Notes: calls `celery_app.control.revoke(str(run_id), terminate=True)` — this revokes by task ID, but the task was enqueued under its own Celery-generated task ID, not the run ID, so revocation by run ID as written does not actually terminate the in-flight Celery task. The DB row's `status` is still force-set to `cancelled` regardless, which is what most callers observe; be aware the underlying `graph.ainvoke` may keep running to completion in the worker process even after this call returns `200`.

### `GET /projects/{project_id}/runs/{run_id}/evidence/{evidence_id}/url`
Auth required.
Response `200`: `{"url": string}` — a MinIO presigned GET URL (1 hour expiry, `EvidenceStorage.presigned_url`). `404` if the evidence row has no binary `storage_key` (i.e. it's an `inline_data`-only evidence type like console/network logs or the accessibility tree) or doesn't belong to the given run.

---

## Reports — `app/api/routers/reports.py`

All routes prefixed `/projects/{project_id}/runs/{run_id}/reports`.

### `GET /projects/{project_id}/runs/{run_id}/reports`
Auth required. Response `200`: `ReportOut[]` — `{id, run_id, format: "markdown"|"pdf"|"json"|"jira", storage_key: string}`.

### `POST /projects/{project_id}/runs/{run_id}/reports`
Auth required.
Request (`ReportGenerateRequest`): `{formats?: ("markdown"|"pdf"|"json"|"jira")[] = ["markdown", "json"]}`
Response `201`: `ReportOut[]`, one per requested format.
Notes: `409` if the run hasn't finished (`run.report_markdown is None`). Markdown and JSON reports are auto-generated and stored at run completion already (`app/execution/tasks.py::_persist_final_state`) — calling this with those formats again generates a **second**, separate `Report` row pointing at a new MinIO key rather than deduplicating. PDF (`render_pdf`, `weasyprint`) is a pure rendering of the already-generated `report_markdown` — no new LLM call. Jira markup (`render_jira`) is a deterministic transform assembled from live `Run` fields at request time (not from the persisted `report_json`, which is only written for the JSON format at run completion).

### `GET /projects/{project_id}/runs/{run_id}/reports/{report_id}/url`
Auth required. Response `200`: `{"url": string}` — presigned MinIO URL. `404` if the report doesn't belong to the given run.

---

## Chat — `app/api/routers/chat.py`

### `POST /chat/message`
Auth required.
Request (`ChatMessageRequest`): `{project_id: uuid, message: string, conversation_id?: uuid}`
Response `200` (`ChatMessageResponse`): `{conversation_id: uuid, answer: string, sources: ChatSource[]}` where `ChatSource` = `{kind: "run"|"knowledge", ref_id: uuid, snippet: string}`.
Notes: grounds the answer in two contexts fetched fresh on every call — up to 20 most recent `Run`s for the project (status/confidence/severity/root-cause, not full step detail) and up to 5 semantic-search hits (`app/rag/retriever.py::semantic_search`) against the project's knowledge base. There is no persisted conversation history — `conversation_id` round-trips (a new one is minted if omitted) but nothing server-side is keyed off it across calls; each call is independent, single-turn context.

---

## WebSocket — `app/api/routers/ws.py`

### `ws://<host>/api/v1/ws/runs/{run_id}`
No explicit auth check on the WebSocket handshake itself (unlike every REST route above, this endpoint has no `get_current_user` dependency).

**Contract:** the server subscribes to the Redis pub/sub channel `stryker:run:{run_id}` (`app/execution/pubsub.py::subscribe`) — the same channel the Celery worker publishes to via `publish_sync` while running the LangGraph pipeline — and forwards every message to the client as JSON, in order, as they're published. The connection closes itself (server-initiated) the moment a message's `run_status` is one of `passed`, `failed`, `errored`, `cancelled` — i.e. exactly once the run reaches a terminal state. There's no replay: connecting after a run has already finished means you may receive zero messages before the socket closes, or the terminal message only if it happens to still be in flight — this endpoint is for **live** progress, not for fetching run history (use `GET /projects/{project_id}/runs/{run_id}` for that).

**Message shape** — `RunStepEvent` (`app/schemas/run.py`), though note the WebSocket handler sends whatever dict `publish_sync` was given rather than validating/serializing through this Pydantic model — treat it as the de facto contract, not a runtime-enforced one:

```json
{
  "run_id": "uuid",
  "step_id": "uuid | null",
  "run_status": "queued|planning|running|retrying|validating|passed|failed|errored|cancelled",
  "step_status": "waiting|running|retrying|passed|failed|skipped | null",
  "sequence": "int | null",
  "name": "string | null",
  "message": "string | null",
  "confidence_score": "float | null"
}
```

In practice the events published by `app/execution/tasks.py` and `app/agents/graph.py`/`app/agents/executor_node.py` populate a subset of these fields depending on the pipeline stage:
- Graph-level milestones (`requirement`/`planner` nodes) publish `{run_status: "planning", message: "Understanding requirement" | "Generating execution plan"}`.
- The executor node publishes one event per step transition: `{run_status: "running", step_status: "running", sequence, name}` when a step starts, then `{run_status: "running", step_status: "passed"|"failed", sequence, name, message: <error, if any>}` when it finishes.
- The validator node publishes `{run_status: "validating", message: "Validating business outcomes"}`.
- The final message on any terminal outcome is `{run_id, run_status: "passed"|"failed"|"errored", confidence_score, message: "Run complete"}` (or, on an unhandled crash inside `graph.ainvoke`, `{run_id, run_status: "errored", message: <exception string>}` published directly from the Celery task's `except` block, bypassing the graph entirely).

None of these include `step_id` — evidence is that field currently goes unused by the publishers despite being part of the schema; consumers should treat `sequence` + `name` as the per-step identifier over the wire, and only look up the real `Step.id` afterward via the REST run-detail endpoint.
