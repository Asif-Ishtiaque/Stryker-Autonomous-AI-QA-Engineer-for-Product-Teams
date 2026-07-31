# Contributing to Stryker

## Running tests

```bash
make test
# equivalent to:
cd backend && pytest
```

Test layout (`backend/tests/`):
- `tests/unit/` — pure unit tests with no external services (e.g. `test_chunker.py`, `test_comparator_agent.py`, `test_credential_cipher.py`, `test_executor_registry.py`). These are the fast tests you should be running constantly while working.
- `tests/integration/` and `tests/e2e/` — reserved for tests that exercise real infrastructure (Postgres, Redis, Chroma, a real browser). Both directories exist in the tree but are currently empty except for `__init__.py` — there is no integration/e2e suite yet. If you're adding the first one, wire it into `pyproject.toml`'s `[tool.pytest.ini_options]` `testpaths` if it needs different fixtures/markers than the unit suite, and document how to bring up its dependencies (e.g. via `docker compose up postgres redis`).

`tests/conftest.py` sets `JWT_SECRET` and `CREDENTIAL_ENCRYPTION_KEY` environment defaults before anything imports `app.core.config`, so the test suite never needs a real `.env` file — keep any new required `Settings` field's test default there too, or tests that import `app.core.config` will fail with a missing-field validation error.

Pytest is configured for `asyncio_mode = "auto"` (`pyproject.toml`), so `async def test_...` functions work without an explicit `@pytest.mark.asyncio` decorator.

## Lint and format

```bash
make fmt    # ruff format . && ruff check --fix .
make lint   # ruff check . && mypy app
```

Both run from `backend/`. Ruff is configured for `line-length = 110`, `target-version = "py312"`, and the `E`, `F`, `I`, `UP`, `B`, `SIM` rule sets (`pyproject.toml`). Mypy runs with the Pydantic plugin enabled and `ignore_missing_imports = true` — type untyped third-party dependencies pragmatically rather than fighting stub gaps, but keep first-party `app/` code fully typed.

Run `make fmt` before `make lint` — most of what `ruff check` would otherwise flag, `ruff format`/`--fix` resolves automatically.

## Branch and PR conventions

- Branch names: `<type>/<short-description>`, e.g. `feat/graphql-executor`, `fix/locator-fuzzy-match`, `docs/api-reference`.
- Keep PRs scoped to one concern. A new `Executor` and an unrelated dependency bump are two PRs.
- Reference the relevant file paths and function/class names in the PR description — the codebase leans on precise references (this doc does too) rather than prose summaries, so reviewers can jump straight to the diff's context.
- If you touch `app/db/models/`, include the generated Alembic migration in the same PR (`make revision m="..."`) — don't leave a model change without its migration.
- If you add or change an environment variable, update `docs/DEPLOYMENT.md`'s variable table in the same PR — `app/core/config.py::Settings` and that table must stay in sync.

## Commit message expectations

Short imperative summary line (`Add GraphQL executor`, `Fix fuzzy locator matching threshold`), optionally followed by a blank line and a paragraph explaining *why*, not just *what* — the diff already shows what changed. Reference file paths when it clarifies scope. No fixed prefix convention (no enforced Conventional Commits) is in place today, but branch-name type prefixes (see above) should match the commit's actual intent.

## Worked example: adding a new knowledge-source parser

This mirrors `app/rag/parsers/pdf.py`, the simplest built-in parser, end to end.

1. **Add the enum value** (if the source type doesn't already exist) in `app/domain/enums.py::KnowledgeSourceType`.
2. **Write the parser function** in a new module under `app/rag/parsers/`, matching the `ParserFn` signature `(raw_bytes: bytes, filename: str) -> list[str]` defined in `app/rag/parsers/base.py`:

   ```python
   # app/rag/parsers/my_format.py
   from __future__ import annotations

   def parse_my_format(raw: bytes, filename: str) -> list[str]:
       # Return a list of plain-text blocks ready for chunking — not raw
       # bytes, not a single giant string if the format has natural
       # boundaries (pages, rows, sections). One block per logical unit
       # gives the chunker (app/rag/chunker.py) better material to work
       # with than one undifferentiated blob.
       ...
       return blocks
   ```

3. **Register it** in `app/rag/parsers/__init__.py`:

   ```python
   from app.rag.parsers.my_format import parse_my_format

   register_parser(KnowledgeSourceType.MY_FORMAT, parse_my_format)
   ```

4. **Map file extensions to the new type** in `app/api/routers/knowledge.py::_EXTENSION_MAP` so uploads with that extension route to it.
5. **Add a unit test** under `tests/unit/` following the pattern of the existing chunker/comparator tests — feed the parser known bytes, assert on the returned blocks.

Nothing in `app/rag/ingestion.py` needs to change — `ingest_document` calls `get_parser(source_type)` and is agnostic to what's registered. This is the same registry pattern used for `Executor`s (`app/agents/executors/base.py`); see [`PLUGIN_GUIDE.md`](PLUGIN_GUIDE.md) for the fully worked Executor and LLM-provider equivalents.

## Adding a new report format

Reports are pure functions of a finished run's data — no new LLM call needed for a new *rendering*:
1. Add the format to `app/domain/enums.py::ReportFormat`.
2. Write a `render_<format>(...)` function under `app/reports/`, following `app/reports/jira_report.py` (deterministic string transform of `report_json`) or `app/reports/pdf_report.py` (transform of the already-generated `report_markdown`) depending on which source data your format needs.
3. Wire it into `app/api/routers/reports.py::generate_reports`'s format dispatch (the `if fmt == ReportFormat...` chain) and give it a MinIO key prefix consistent with the others (`reports/{run.id}`).
4. Update `ReportGenerateRequest`'s default in `app/schemas/report.py` only if the new format should be auto-generated by default — most formats are on-demand, matching the "Markdown + JSON auto-generated at run completion; PDF and Jira-markup generated on demand" split described in the README.

## Code of conduct

Be direct, be kind, assume good faith. Disagree about code in the PR thread, not about people. Anything that would make a contributor feel unwelcome — including in commit messages, code review tone, or issue discussion — isn't acceptable here, full stop. If a situation comes up that this paragraph doesn't obviously cover, use the same judgment you'd want applied to you, and raise it with the maintainers if you're unsure.
