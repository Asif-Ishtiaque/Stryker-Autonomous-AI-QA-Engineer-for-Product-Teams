"""OpenTelemetry tracing + Prometheus metrics wiring.

Kept isolated from app.main so tracing can be disabled entirely in local
dev (ENABLE_TRACING=false) without touching route code — every route and
Celery task is instrumented via the auto-instrumentors below, not by hand.
"""
from __future__ import annotations

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_fastapi_instrumentator import Instrumentator

from app.core.config import Settings


def configure_telemetry(app: FastAPI, settings: Settings) -> None:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)

    if not settings.enable_tracing:
        return

    resource = Resource.create({SERVICE_NAME: settings.app_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument()
