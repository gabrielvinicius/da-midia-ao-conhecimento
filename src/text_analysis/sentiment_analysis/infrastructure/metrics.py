"""Prometheus metrics collectors used by the sentiment analysis module."""

from prometheus_client import Counter, Histogram

from src.shared.infrastructure.prometheus_metrics import shared_metrics


class PrometheusSentimentMetrics:
    """Expose convenience wrappers around Prometheus primitives.
    Uses shared metrics to prevent duplicate registration in Celery workers.
    """

    def __init__(self) -> None:
        # Use shared metrics to prevent duplicate registration
        self._counter = shared_metrics.get_sentiment_analysis_events_total()
        self._histogram = shared_metrics.get_sentiment_analysis_processing_seconds()

    def increment_counter(self, metric: str) -> None:
        self._counter.labels(metric=metric).inc()

    def record_histogram(self, metric: str, value: float) -> None:
        self._histogram.labels(metric=metric).observe(value)

    def record_operation(
        self,
        *,
        operation: str,
        provider: str,
        duration: float,
        success: bool,
    ) -> None:
        status_metric = f"{operation}.success" if success else f"{operation}.failed"
        self.increment_counter(status_metric)
        self.record_histogram(f"{operation}.duration", duration)


__all__ = ["PrometheusSentimentMetrics"]

