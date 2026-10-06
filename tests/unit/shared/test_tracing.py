from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.shared.infrastructure.observability.tracing import tracer as tracing


def _capture_provider(monkeypatch):
    captured = {}
    monkeypatch.setattr(tracing.trace, "set_tracer_provider", lambda p: captured.setdefault("p", p))
    return captured


def _processors(provider):
    return list(provider._active_span_processor._span_processors)


def test_spans_are_exported_via_otlp_when_endpoint_is_set(monkeypatch):
    captured = _capture_provider(monkeypatch)
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4318")

    tracing.configure_tracer("teste")

    processors = _processors(captured["p"])
    assert len(processors) == 1 and isinstance(processors[0], BatchSpanProcessor)


def test_no_exporter_without_endpoint(monkeypatch):
    captured = _capture_provider(monkeypatch)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)

    tracing.configure_tracer("teste")

    assert _processors(captured["p"]) == []
