"""Prometheus metrics collectors used by the sentiment analysis module."""

from prometheus_client import Counter, Histogram


class PrometheusSentimentMetrics:
    """Expose convenience wrappers around Prometheus primitives."""

    def __init__(self) -> None:
        self._counter = Counter(
            "sentiment_analysis_events_total",
            "Total number of sentiment analysis events emitted.",
            labelnames=("metric",),
        )
        self._histogram = Histogram(
            "sentiment_analysis_processing_seconds",
            "Observed processing time for sentiment analysis operations.",
            labelnames=("metric",),
        )

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

