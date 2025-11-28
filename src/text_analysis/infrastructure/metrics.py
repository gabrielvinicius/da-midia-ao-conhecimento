"""Prometheus metrics implementation for text analysis."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

from src.shared.infrastructure.prometheus_metrics import shared_metrics
from src.text_analysis.application.metrics import TextAnalysisMetrics


class PrometheusTextAnalysisMetrics(TextAnalysisMetrics):
    def __init__(self) -> None:
        self._operations_total: Counter = shared_metrics.get_text_analysis_operations_total()
        self._duration_seconds: Histogram = shared_metrics.get_text_analysis_duration_seconds()

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
        self._operations_total.labels(operation=operation, provider=provider_label, status=status, media_id=media_label).inc()
        self._duration_seconds.labels(operation=operation, provider=provider_label, media_id=media_label, status=status).observe(duration)

    def set_media_context(self, media_id: str | None):
        self._media_id = media_id or "unknown"


__all__ = ["PrometheusTextAnalysisMetrics"]
