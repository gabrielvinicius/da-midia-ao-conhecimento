"""Configuração do rastreamento distribuído (OpenTelemetry)."""
from __future__ import annotations

import os

import structlog
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider

logger = structlog.get_logger(__name__)

OTLP_ENDPOINT_ENV = "OTEL_EXPORTER_OTLP_ENDPOINT"


def configure_tracer(service_name: str) -> trace.Tracer:
    """Configura o provedor global de tracing.

    Se ``OTEL_EXPORTER_OTLP_ENDPOINT`` estiver definido (ex.:
    ``http://jaeger:4318``), os spans são enviados via OTLP/HTTP; o Jaeger
    recebe OTLP nativamente. Sem a variável, os spans são criados mas não
    exportados, o que mantém testes e execuções locais sem dependência externa.
    """
    provider = TracerProvider(resource=Resource(attributes={SERVICE_NAME: service_name}))

    endpoint = os.getenv(OTLP_ENDPOINT_ENV)
    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
            from opentelemetry.sdk.trace.export import BatchSpanProcessor

            # O exportador lê OTEL_EXPORTER_OTLP_ENDPOINT e acrescenta /v1/traces.
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
            logger.info("tracing.otlp_enabled", service=service_name, endpoint=endpoint)
        except Exception as exc:  # exportador ausente não pode derrubar a aplicação
            logger.warning("tracing.otlp_unavailable", error=str(exc))
    else:
        logger.info("tracing.export_disabled", service=service_name)

    trace.set_tracer_provider(provider)
    return trace.get_tracer(service_name)
