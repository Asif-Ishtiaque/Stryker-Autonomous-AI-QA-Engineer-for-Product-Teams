"""Provider-agnostic LLM interface.

Every agent in app.agents talks to this Protocol only — never to a specific
SDK — so swapping Ollama for vLLM, LM Studio, or any OpenAI-compatible
endpoint is a config change (STRYKER_LLM_PROVIDER), not a code change.
"""
from __future__ import annotations

import json
from typing import Any, Protocol

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # "system" | "user" | "assistant"
    content: str


def parse_json_object(raw: str) -> dict[str, Any]:
    """Parses an LLM's JSON response, tolerating the most common way smaller
    local models violate a requested object schema: wrapping it in a
    single-element array (`[{...}]` instead of `{...}`). Every agent that
    asks for `json_schema`-shaped output should parse through this rather
    than calling `json.loads` directly and indexing straight into the
    result — a raw `parsed["key"]` on an unexpectedly-list response fails
    with a cryptic `TypeError: list indices must be integers or slices, not
    str` that gives no hint what actually went wrong.
    """
    parsed = json.loads(raw)
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
        return parsed[0]
    raise ValueError(f"Expected a JSON object from the LLM, got {type(parsed).__name__}: {raw[:200]!r}")


class LLMProvider(Protocol):
    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        json_schema: dict | None = None,
        temperature: float | None = None,
    ) -> str:
        """Return the assistant's text response. If json_schema is given, the
        provider must return text that parses as JSON matching that schema
        (achieved via structured-output mode where supported, or a strict
        system-prompt instruction + retry loop otherwise)."""
        ...


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    @property
    def dimensions(self) -> int: ...
