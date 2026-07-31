"""Central application configuration.

Every external dependency (LLM provider, embeddings model, storage, queue) is
selected here from environment variables — never hardcoded in application
code — so the whole platform can be reconfigured to point at different open
source infra (or a different LLM provider) without touching a single line
outside this file.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LLMProviderName = Literal["ollama", "vllm", "lmstudio", "openai_compatible"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    app_name: str = "Stryker"
    environment: Literal["development", "staging", "production"] = "development"
    api_prefix: str = "/api/v1"
    debug: bool = True
    frontend_url: str = "http://localhost:3000"

    # --- Security ---
    jwt_secret: str = Field(..., description="Secret used to sign access/refresh JWTs")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 14
    credential_encryption_key: str = Field(
        ..., description="32-byte urlsafe-base64 Fernet key used to encrypt stored AUT credentials"
    )

    # --- Database ---
    database_url: str = "postgresql+asyncpg://stryker:stryker@postgres:5432/stryker"

    # --- Redis / Celery ---
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # --- Vector store (knowledge base) ---
    chroma_host: str = "chroma"
    chroma_port: int = 8000
    chroma_collection_prefix: str = "stryker_kb"

    # --- Object storage (evidence artifacts) ---
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "stryker"
    minio_secret_key: str = "stryker-secret"
    minio_secure: bool = False
    minio_evidence_bucket: str = "stryker-evidence"

    # --- Search (execution history / log search) ---
    opensearch_url: str = "http://opensearch:9200"
    opensearch_index_prefix: str = "stryker-runs"

    # --- Observability ---
    otel_exporter_otlp_endpoint: str = "http://otel-collector:4317"
    enable_tracing: bool = True

    # --- LLM provider (reasoning) ---
    llm_provider: LLMProviderName = "ollama"
    llm_model: str = "llama3.1"
    llm_base_url: str = "http://ollama:11434/v1"
    llm_api_key: str = "not-needed"
    llm_temperature: float = 0.1
    llm_request_timeout_seconds: int = 120

    # --- Embeddings provider (RAG) ---
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_device: str = "cpu"

    # --- Execution engine ---
    browser_pool_size: int = 4
    browser_headless: bool = True
    max_plan_retries: int = 2
    default_step_timeout_ms: int = 15000
    max_concurrent_runs: int = 50


@lru_cache
def get_settings() -> Settings:
    return Settings()
