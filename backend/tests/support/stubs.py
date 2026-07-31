"""Shared test doubles for integration and e2e tests.

These stand in for every piece of *real external infra* the app talks to
(LLM provider, embeddings model, Chroma, MinIO) at the network edge — the
functions/classes here implement the same protocol the real thing does, so
application code never has to know it's talking to a stub.

Deliberately lives outside tests/unit — it's shared plumbing for
tests/integration and tests/e2e, not a unit test itself.
"""
from __future__ import annotations

import json
import uuid
from typing import Any

DEFAULT_REQUIREMENT_RESPONSE: dict[str, Any] = {
    "understood_intent": "The user can complete the described action and see the expected result.",
    "expected_outcomes": ["The expected outcome is visibly confirmed on screen"],
    "inferred_validations": ["An audit trail of the action exists"],
    "identified_risks": ["Silent failure could go unnoticed in production"],
    "predicted_edge_cases": ["Invalid input", "Concurrent attempts"],
    "confidence": 0.9,
}

DEFAULT_PLAN_STEPS: list[dict[str, Any]] = [
    {
        "sequence": 1,
        "name": "Navigate to home",
        "action_type": "navigate",
        "parameters": {"url": "/"},
        "expected_outcome": "Home page loads",
    },
]

DEFAULT_FINDINGS: list[dict[str, Any]] = [
    {
        "checked": "The expected outcome is visibly confirmed on screen",
        "outcome": "met",
        "evidence": "stub evidence",
        "confidence": 0.9,
    }
]

DEFAULT_ROOT_CAUSE: dict[str, Any] = {
    "root_cause_hypothesis": "Stub root cause hypothesis for testing.",
    "severity": "medium",
}

DEFAULT_REPORT_MARKDOWN = "## Executive Summary\nStub report generated for testing purposes.\n"


class StubLLMProvider:
    """Implements the LLMProvider Protocol (see app.llm.base).

    Inspects the json_schema each caller passes and returns whatever canned
    JSON matches that schema's shape, so every agent in the pipeline
    (RequirementAgent, PlannerAgent, ValidatorAgent, ComparatorAgent,
    ReportAgent, and the self-healing locator's LLM fallback) gets a
    plausible, schema-valid response without ever hitting a real model.
    """

    def __init__(
        self,
        *,
        requirement_response: dict[str, Any] | None = None,
        plan_steps: list[dict[str, Any]] | None = None,
        findings: list[dict[str, Any]] | None = None,
        root_cause: dict[str, Any] | None = None,
        report_markdown: str | None = None,
        semantic_match: dict[str, Any] | None = None,
    ) -> None:
        self.calls: list[tuple[list, dict | None]] = []
        self.semantic_disambiguation_calls = 0
        self._requirement_response = requirement_response or DEFAULT_REQUIREMENT_RESPONSE
        self._plan_steps = DEFAULT_PLAN_STEPS if plan_steps is None else plan_steps
        self._findings = DEFAULT_FINDINGS if findings is None else findings
        self._root_cause = root_cause or DEFAULT_ROOT_CAUSE
        self._report_markdown = report_markdown or DEFAULT_REPORT_MARKDOWN
        self._semantic_match = semantic_match

    async def chat(
        self,
        messages: list[Any],
        *,
        json_schema: dict | None = None,
        temperature: float | None = None,
    ) -> str:
        self.calls.append((messages, json_schema))

        if json_schema is None:
            return self._report_markdown

        props = set(json_schema.get("properties", {}).keys())

        if {"understood_intent", "expected_outcomes"} <= props:
            return json.dumps(self._requirement_response)
        if "steps" in props:
            return json.dumps({"steps": self._plan_steps})
        if "findings" in props:
            return json.dumps({"findings": self._findings})
        if {"root_cause_hypothesis", "severity"} <= props:
            return json.dumps(self._root_cause)
        if {"index", "confidence"} <= props:
            self.semantic_disambiguation_calls += 1
            match = self._semantic_match or {"index": -1, "confidence": 0.0}
            return json.dumps(match)

        return "{}"


class StubEmbeddingProvider:
    """Implements the EmbeddingProvider Protocol with fixed-length zero vectors."""

    def __init__(self, dims: int = 8) -> None:
        self._dims = dims

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * self._dims for _ in texts]

    @property
    def dimensions(self) -> int:
        return self._dims


class _FakeChromaCollection:
    def __init__(self) -> None:
        self._ids: list[str] = []

    def count(self) -> int:
        return len(self._ids)

    def query(self, query_embeddings: list[list[float]], n_results: int) -> dict:
        return {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    def upsert(self, ids: list[str], embeddings: list, documents: list[str], metadatas: list[dict]) -> None:
        self._ids.extend(ids)


class StubChromaClient:
    """Implements the ChromaClientWrapper surface used by app.rag.* without a real Chroma server."""

    def __init__(self) -> None:
        self._collections: dict[uuid.UUID, _FakeChromaCollection] = {}
        self.deleted: list[uuid.UUID] = []

    def collection_name(self, project_id: uuid.UUID) -> str:
        return f"stryker_kb_{project_id.hex}"

    def get_or_create_collection(self, project_id: uuid.UUID) -> _FakeChromaCollection:
        return self._collections.setdefault(project_id, _FakeChromaCollection())

    def delete_collection(self, project_id: uuid.UUID) -> None:
        self._collections.pop(project_id, None)
        self.deleted.append(project_id)


class InMemoryEvidenceStorage:
    """Implements the EvidenceStorage surface (put_bytes/get_bytes/presigned_url) over a dict
    instead of a real MinIO server."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_bytes(self, key_prefix: str, data: bytes, content_type: str, extension: str = "") -> str:
        key = f"{key_prefix}/{uuid.uuid4()}{extension}"
        self.objects[key] = data
        return key

    def get_bytes(self, key: str) -> bytes:
        return self.objects[key]

    def presigned_url(self, key: str, expires_seconds: int = 3600) -> str:
        return f"memory://{key}"


class FakeSuccessExecutor:
    """A minimal Executor (see app.agents.executors.base.Executor) that reports every step as
    passed without touching Playwright/HTTP/anything real — used to prove the LangGraph pipeline
    and DB-persistence path wire together end-to-end without needing a real browser.

    Deliberately duck-types the Executor ABC's public surface rather than subclassing it, so this
    module has no import-time dependency on app.agents.executors.base.
    """

    platform = "fake"

    def __init__(self, base_url: str, credential: dict | None, on_event, llm) -> None:
        self.base_url = base_url
        self.credential = credential
        self.on_event = on_event
        self.llm = llm

    async def setup(self) -> None:
        return None

    async def teardown(self) -> None:
        return None

    async def execute_step(self, step: dict) -> dict:
        return {
            "sequence": step["sequence"],
            "status": "passed",
            "result": {"ok": True, "action_type": step["action_type"]},
            "error_message": None,
            "evidence_refs": [
                {
                    "evidence_type": "screenshot",
                    "storage_key": f"fake/{step['sequence']}-{uuid.uuid4()}.png",
                    "content_type": "image/png",
                }
            ],
        }
