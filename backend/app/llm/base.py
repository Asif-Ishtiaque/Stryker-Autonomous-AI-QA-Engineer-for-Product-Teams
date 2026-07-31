"""Provider-agnostic LLM interface.

Every agent in app.agents talks to this Protocol only — never to a specific
SDK — so swapping Ollama for vLLM, LM Studio, or any OpenAI-compatible
endpoint is a config change (STRYKER_LLM_PROVIDER), not a code change.
"""
from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str  # "system" | "user" | "assistant"
    content: str


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
