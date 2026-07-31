"""Factory that resolves Settings.llm_provider into a concrete LLMProvider.

Ollama, vLLM, and LM Studio all expose an OpenAI-compatible `/v1/chat/completions`
endpoint, so they share one adapter — this factory only decides which base_url
convention/default to apply. Adding a genuinely different wire protocol later
(e.g. a native Anthropic-style API) means adding one branch here and nowhere else.
"""
from __future__ import annotations

from functools import lru_cache

from app.core.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.providers.openai_compatible import OpenAICompatibleProvider


def build_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider in ("ollama", "vllm", "lmstudio", "openai_compatible"):
        return OpenAICompatibleProvider(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            timeout_seconds=settings.llm_request_timeout_seconds,
        )
    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")


@lru_cache
def get_llm_provider() -> LLMProvider:
    return build_llm_provider(get_settings())
