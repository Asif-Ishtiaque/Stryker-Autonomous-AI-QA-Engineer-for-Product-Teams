"""Client for any OpenAI-compatible chat-completions endpoint.

This single class serves Ollama (`/v1`), vLLM's OpenAI server, LM Studio's
local server, and real OpenAI-compatible APIs — they all speak the same
wire protocol, so one adapter covers all four LLM_PROVIDER options in the
spec. Only the base_url/api_key differ, and those come from Settings.
"""
from __future__ import annotations

import json

from openai import AsyncOpenAI

from app.llm.base import ChatMessage


class OpenAICompatibleProvider:
    def __init__(self, base_url: str, api_key: str, model: str, timeout_seconds: int = 120) -> None:
        self._client = AsyncOpenAI(base_url=base_url, api_key=api_key, timeout=timeout_seconds)
        self._model = model

    async def chat(
        self,
        messages: list[ChatMessage],
        *,
        json_schema: dict | None = None,
        temperature: float | None = None,
    ) -> str:
        kwargs: dict = {}
        if json_schema is not None:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": "stryker_output", "schema": json_schema, "strict": True},
            }

        try:
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": m.role, "content": m.content} for m in messages],
                temperature=temperature if temperature is not None else 0.1,
                **kwargs,
            )
        except Exception:
            if json_schema is None:
                raise
            # Not every OpenAI-compatible server (Ollama, LM Studio) implements
            # response_format=json_schema — fall back to a strict prompt instruction.
            fallback_messages = [
                *messages,
                ChatMessage(
                    role="system",
                    content=(
                        "Respond with ONLY valid JSON matching this schema, no prose, "
                        f"no markdown fences: {json.dumps(json_schema)}"
                    ),
                ),
            ]
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": m.role, "content": m.content} for m in fallback_messages],
                temperature=temperature if temperature is not None else 0.1,
            )
        return response.choices[0].message.content or ""
