"""Factory that resolves Settings.llm_provider into a concrete LLMProvider.

Ollama, vLLM, and LM Studio all expose an OpenAI-compatible `/v1/chat/completions`
endpoint, so they share one adapter — this factory only decides which base_url
convention/default to apply. Adding a genuinely different wire protocol later
(e.g. a native Anthropic-style API) means adding one branch here and nowhere else.
"""
from __future__ import annotations

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


def get_llm_provider() -> LLMProvider:
    # Deliberately NOT @lru_cache'd. The provider owns an AsyncOpenAI client, whose
    # underlying httpx connection pool binds to whatever asyncio event loop is running
    # when it's first used. That's fine for FastAPI (one event loop for the process's
    # whole life) but not for Celery: each task runs via asyncio.run(), which tears the
    # loop down when the task finishes. A cached client from task N reused in task N+1
    # (same worker process, fresh loop) doesn't cleanly error like the DB pool did (see
    # dispose_stale_pool in app/db/session.py for that sibling bug) — it silently hangs
    # forever on the next request instead, which is far worse: no error, no timeout, the
    # run just sits at "planning" indefinitely. Constructing a fresh client per call is
    # negligible cost next to actual LLM call latency (60-150s+ against local CPU inference).
    return build_llm_provider(get_settings())
