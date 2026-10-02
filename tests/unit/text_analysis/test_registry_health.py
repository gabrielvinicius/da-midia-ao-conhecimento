from unittest.mock import MagicMock

from src.text_analysis.bootstrap import _update_registry_availability
from src.text_analysis.infrastructure.dependencies import registry


def test_registry_marks_unavailable_when_imports_fail(monkeypatch):
    # Mock availability helper
    def mock_check(name):
        if name in ("transformers", "bertopic", "sklearn", "numpy"):
            return False
        return True

    monkeypatch.setattr("src.text_analysis.bootstrap._check_module_available", mock_check)

    # force httpx failure
    class _FailClient:
        def __init__(self, *_, **__):
            pass
        def __enter__(self):
            raise RuntimeError("fail")
        def __exit__(self, *exc):
            return False
    monkeypatch.setattr("httpx.Client", _FailClient, raising=False)

    # Force health refresh
    monkeypatch.setattr("src.text_analysis.infrastructure.dependencies.registry.needs_health_refresh", lambda: True)

    # Mock metrics
    from src.shared.infrastructure.observability.metrics.prometheus_metrics import SharedPrometheusMetrics
    monkeypatch.setattr(SharedPrometheusMetrics, "get_provider_health_checks_total", MagicMock())

    _update_registry_availability()

    assert any(not e.available for e in registry.TEXT_GEN_PROVIDERS if e.name.startswith("hf:"))
    assert any(not e.available for e in registry.TOPIC_PROVIDERS if e.name == "bertopic")
    assert any(not e.available for e in registry.TOPIC_PROVIDERS if e.name == "tfidf")