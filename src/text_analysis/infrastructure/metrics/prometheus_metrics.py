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
        
        labels = (operation, provider_label, status)
        
        try:
            self._operations_total.labels(*labels).inc()
            self._duration_seconds.labels(*labels).observe(duration)
        except ValueError:
            # Fallback if labels don't match (e.g. older version registered in REGISTRY)
            # This avoids crashing the whole analysis task just because metrics failed
            pass


__all__ = ["PrometheusTextAnalysisMetrics"]
