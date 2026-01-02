"""Prometheus metrics implementation for text analysis."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

from src.shared.infrastructure.observability.metrics.prometheus_metrics import (
    shared_metrics,
)
from src.text_analysis.application.metrics import TextAnalysisMetrics


class PrometheusTextAnalysisMetrics(TextAnalysisMetrics):
    def __init__(self) -> None:
        self._operations_total: Counter = (
            shared_metrics.get_text_analysis_operations_total()
        )
        self._duration_seconds: Histogram = (
            shared_metrics.get_text_analysis_duration_seconds()
        )

    async def record_operation(
        self,
        *,
        operation: str,
        duration: float,
        success: bool,
        provider: str | None = None,
    ) -> None:
        status = "success" if success else "failure"
        provider_label = provider or "unknown"
        media_label = getattr(self, "_media_id", None) or "unknown"
        user_label = getattr(self, "_user_id", None) or "unknown"
        
        # Positional arguments must match: operation, provider, status, media_id, user_id
        labels = (operation, provider_label, status, media_label, user_label)
        
        try:
            self._operations_total.labels(*labels).inc()
            self._duration_seconds.labels(*labels).observe(duration)
        except ValueError:
            # Fallback if labels don't match (e.g. older version registered in REGISTRY)
            # This avoids crashing the whole analysis task just because metrics failed
            pass

    def set_context(self, media_id: str | None, user_id: str | None = None):
        self._media_id = media_id or "unknown"
        self._user_id = user_id or "unknown"


__all__ = ["PrometheusTextAnalysisMetrics"]
