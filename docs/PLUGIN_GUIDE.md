# Plugin Guide

Stryker has three extensibility seams, each the same shape: a small ABC or function-signature contract, plus a `register_*` call that populates a module-level registry looked up by a string key. Nothing upstream of the registry (the planner, the ingestion pipeline, the agent graph) branches on which concrete implementation is registered — that's the whole point. This guide works through one fully worked example for each seam, each mirroring a real file already in the codebase.

## (a) Adding a new Executor for a new platform

**Mirrors:** `app/agents/executors/web/playwright_executor.py` (`WebExecutor`), the only executor implemented today.

### The contract

`app/agents/executors/base.py`:

```python
class Executor(ABC):
    platform: str

    def __init__(self, base_url: str, credential: dict[str, Any] | None, on_event: StepEventSink, llm: LLMProvider) -> None: ...

    @abstractmethod
    async def setup(self) -> None: ...

    @abstractmethod
    async def execute_step(self, step: PlannedStep) -> ExecutedStepResult: ...

    @abstractmethod
    async def teardown(self) -> None: ...
```

One `Executor` instance is created per Run (`app/agents/executor_node.py::run_executor_node`) and used for every step in that run's plan, in order. `PlannedStep` and `ExecutedStepResult` are the two TypedDicts in `app/agents/state.py` — your executor is the boundary that translates a platform-agnostic step into a platform-specific action and back into a platform-agnostic result.

### Worked example: a REST API executor

Say you want `Platform.REST_API` (already in `app/domain/enums.py`, already selectable when creating a `Project`, but with no executor registered — creating a run against it today raises `ValueError: No executor registered for platform 'rest_api'`).

```python
# app/agents/executors/api/rest_executor.py
from __future__ import annotations

import time
from typing import Any

import httpx

from app.agents.executors.base import Executor
from app.agents.state import ExecutedStepResult, PlannedStep


class RestApiExecutor(Executor):
    platform = "rest_api"

    async def setup(self) -> None:
        headers = {}
        if self.credential:
            if self.credential.get("bearer_token"):
                headers["Authorization"] = f"Bearer {self.credential['bearer_token']}"
            if self.credential.get("headers"):
                headers.update(self.credential["headers"])
        self._client = httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=30.0)

    async def teardown(self) -> None:
        await self._client.aclose()

    async def execute_step(self, step: PlannedStep) -> ExecutedStepResult:
        started = time.monotonic()
        params = step["parameters"]
        try:
            response = await self._client.request(
                params.get("method", "GET"),
                params.get("path", "/"),
                json=params.get("body"),
                headers=params.get("headers"),
            )
            status = "passed" if response.status_code < 400 else "failed"
            result = {"status_code": response.status_code, "body": _safe_json(response)}
            error_message = None if status == "passed" else f"HTTP {response.status_code}"
        except Exception as exc:  # noqa: BLE001 — a failed step is a normal outcome
            status, result, error_message = "failed", {}, str(exc)

        return ExecutedStepResult(
            sequence=step["sequence"],
            status=status,
            result=result,
            error_message=error_message,
            evidence_refs=[
                {
                    "evidence_type": "api_response",
                    "inline_data": result,
                    "content_type": "application/json",
                },
                {
                    "evidence_type": "timing",
                    "inline_data": {"duration_ms": int((time.monotonic() - started) * 1000)},
                    "content_type": "application/json",
                },
            ],
        )


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {"raw": response.text[:2000]}
```

Register it exactly where `WebExecutor` is registered, in `app/agents/executors/__init__.py`:

```python
from app.agents.executors.api.rest_executor import RestApiExecutor

register_executor("web", WebExecutor)
register_executor("rest_api", RestApiExecutor)
```

That's it — nothing in `app/agents/graph.py`, `app/agents/executor_node.py`, or any of the five LangGraph agents needs to change. The `PlannerAgent`'s system prompt (`app/agents/planner_agent.py`) already describes the `api_call` action type (`{"method", "path", "body", "headers"}`) for exactly this case, since the plan shape was designed platform-agnostic from the start.

**What you're responsible for getting right:**
- `evidence_refs` entries must match the shape `{evidence_type, storage_key|inline_data, content_type}` consumed by `_persist_final_state` in `app/execution/tasks.py` — use one of the `EvidenceType` enum values (`app/domain/enums.py`) for `evidence_type`, even though it's typed as a plain string in `ExecutedStepResult`.
- `teardown()` must never raise — `run_executor_node` calls it inside a `finally` block, and an exception there would mask whatever actually failed.
- If your platform has no equivalent of "self-healing locator" (e.g. a REST API doesn't have UI elements to fuzzy-match), that's fine — not every executor needs a resolution cascade like `SelfHealingLocator`. That machinery is specific to `WebExecutor`, not part of the `Executor` contract.

## (b) Adding a new knowledge-source parser

**Mirrors:** `app/rag/parsers/pdf.py`.

### The contract

`app/rag/parsers/base.py`:

```python
ParserFn = Callable[[bytes, str], list[str]]

def register_parser(source_type: KnowledgeSourceType, fn: ParserFn) -> None: ...
def get_parser(source_type: KnowledgeSourceType) -> ParserFn: ...
```

A parser takes the raw uploaded bytes and the original filename, and returns a list of plain-text blocks. `app/rag/ingestion.py::ingest_document` calls `get_parser(source_type)`, runs every returned block through `chunk_text` (`app/rag/chunker.py`), embeds the resulting chunks, and upserts them into the project's Chroma collection. The parser's only job is turning arbitrary bytes into blocks worth chunking — it doesn't touch embeddings, Chroma, or chunk sizing.

### Worked example: a `.eml` (email) parser

```python
# app/rag/parsers/eml_parser.py
from __future__ import annotations

import email
from email.policy import default as email_default_policy


def parse_eml(raw: bytes, filename: str) -> list[str]:
    message = email.message_from_bytes(raw, policy=email_default_policy)
    blocks: list[str] = [
        f"[{filename}] From: {message.get('From', '')} | Subject: {message.get('Subject', '')}"
    ]

    body = message.get_body(preferencelist=("plain",))
    if body:
        text = body.get_content().strip()
        if text:
            blocks.append(text)

    return blocks
```

Register it, matching `pdf.py`'s registration in `app/rag/parsers/__init__.py`:

```python
from app.rag.parsers.eml_parser import parse_eml

register_parser(KnowledgeSourceType.EML, parse_eml)  # add EML to KnowledgeSourceType first
```

Then map the file extension in `app/api/routers/knowledge.py::_EXTENSION_MAP`:

```python
_EXTENSION_MAP = {
    ...,
    ".eml": KnowledgeSourceType.EML,
}
```

Nothing in `app/rag/ingestion.py`, `app/rag/chunker.py`, or `app/rag/chroma_client.py` needs to change. See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the same worked example with slightly different framing (it's the canonical "add a parser" walkthrough referenced from the contributor workflow doc).

## (c) Adding a new LLM provider

**Mirrors:** `app/llm/providers/openai_compatible.py` (`OpenAICompatibleProvider`), which today serves all four `LLM_PROVIDER` values (`ollama`, `vllm`, `lmstudio`, `openai_compatible`) because they all speak the same OpenAI-style `/v1/chat/completions` wire protocol.

### The contract

`app/llm/base.py`:

```python
class LLMProvider(Protocol):
    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        json_schema: dict | None = None,
        temperature: float | None = None,
    ) -> str: ...
```

Every agent (`app/agents/requirement_agent.py`, `planner_agent.py`, `validator_agent.py`, `comparator_agent.py`, `report_agent.py`) and the locator engine's semantic-disambiguation fallback (`app/agents/executors/web/locator_engine.py`) call `llm.chat(...)` through this Protocol only — never a concrete SDK class. It's structural typing (`Protocol`, not an ABC), so a new provider doesn't need to subclass anything, only match the method signature.

The contract for `json_schema`: when given, `chat()` must return text that parses as JSON matching that schema. `OpenAICompatibleProvider` achieves this via OpenAI's `response_format={"type": "json_schema", ...}` where the server supports it (real OpenAI, some vLLM configs), and falls back to a strict system-prompt instruction (appending a message that repeats the schema and demands JSON-only, no fences) when the call fails — Ollama and LM Studio don't reliably implement `response_format=json_schema`, so every agent's structured-output call still needs to work against them.

### Worked example: a native Anthropic-API provider

This is the case the factory's docstring calls out explicitly: a *genuinely different wire protocol*, not another OpenAI-compatible server.

```python
# app/llm/providers/anthropic_native.py
from __future__ import annotations

import json

from anthropic import AsyncAnthropic

from app.llm.base import ChatMessage


class AnthropicNativeProvider:
    def __init__(self, api_key: str, model: str, timeout_seconds: int = 120) -> None:
        self._client = AsyncAnthropic(api_key=api_key, timeout=timeout_seconds)
        self._model = model

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        json_schema: dict | None = None,
        temperature: float | None = None,
    ) -> str:
        system = "\n".join(m.content for m in messages if m.role == "system") or None
        turns = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]

        if json_schema is not None:
            instruction = (
                "Respond with ONLY valid JSON matching this schema, no prose, no markdown fences: "
                f"{json.dumps(json_schema)}"
            )
            system = f"{system}\n\n{instruction}" if system else instruction

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=system,
            messages=turns,
            temperature=temperature if temperature is not None else 0.1,
        )
        return "".join(block.text for block in response.content if block.type == "text")
```

Wire it into the factory, `app/llm/registry.py::build_llm_provider`:

```python
from app.llm.providers.anthropic_native import AnthropicNativeProvider

def build_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider in ("ollama", "vllm", "lmstudio", "openai_compatible"):
        return OpenAICompatibleProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_request_timeout_seconds,
        )
    if settings.llm_provider == "anthropic":
        return AnthropicNativeProvider(
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_request_timeout_seconds,
        )
    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
```

And add `"anthropic"` to the `LLMProviderName` `Literal` in `app/core/config.py` so `LLM_PROVIDER=anthropic` validates. No agent file changes — every call site already goes through `get_llm_provider()` (`app/llm/registry.py`, `@lru_cache`-wrapped so the provider is built once per process) and the `LLMProvider` Protocol.

**Why this one is worth doing as its own class instead of extending `OpenAICompatibleProvider`:** the whole reason Ollama/vLLM/LM Studio/generic-OpenAI-compatible share one class is that they share one wire format. A provider with a genuinely different request/response shape (native Anthropic Messages API, a gRPC-based provider, anything that isn't `/v1/chat/completions`) belongs in its own class implementing the same `LLMProvider` Protocol — bending `OpenAICompatibleProvider` to also speak a second protocol via internal branching would undo the reason it's simple.
