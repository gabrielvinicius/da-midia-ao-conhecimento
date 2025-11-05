# src/metrics/infrastructure/prometheus_provider.py
from typing import Dict, List, Optional

import structlog
from prometheus_client import Counter, Gauge, Histogram, Summary, generate_latest

from src.monitoring.domain.interfaces import IMetricsProvider

logger = structlog.get_logger(__name__)


class PrometheusMetricsProvider(IMetricsProvider):
    """Prometheus metrics provider following SOLID principles.
    
    Single Responsibility: Handle Prometheus-specific metric operations.
    Open/Closed: Extensible for new metric types.
    Dependency Inversion: Implements IMetricsProvider interface.
    """

    def __init__(self):
        # --- HTTP Metrics ---
        self.REQUEST_COUNT = Counter(
            'http_requests_total',
            'Total HTTP Requests',
            ['method', 'endpoint', 'status_code']
        )
        self.REQUEST_LATENCY = Histogram(
            'http_request_duration_seconds',
            'HTTP Request Latency',
            ['method', 'endpoint']
        )

        # --- Business Metrics (Refactored for generic Media) ---
        self.MEDIA_UPLOADS_TOTAL = Counter(
            'media_uploads_total',
            'Total media files uploaded',
            ['status']
        )
        self.TRANSCRIPTIONS_TOTAL = Counter(
            'transcriptions_total',
            'Total transcriptions processed',
            ['status']
        )
        self.SUMMARIZATIONS_TOTAL = Counter(
            'summarizations_total',
            'Total summaries generated',
            ['status']
        )

        # --- Service Duration Metrics with Provider Label (Refactored for generic Media) ---
        self.UPLOAD_DURATION = Histogram(
            'upload_duration_seconds',
            'Upload processing time per media item',
            ['media_id', 'provider']
        )
        self.TRANSCRIPTION_DURATION = Histogram(
            'transcription_duration_seconds',
            'Transcription processing time per media item',
            ['media_id', 'provider']
        )
        self.SUMMARIZATION_DURATION = Histogram(
            'summarization_duration_seconds',
            'Summarization processing time per media item',
            ['media_id', 'provider']
        )

    def increment_counter(self, name: str, labels: Optional[Dict[str, str]] = None, value: float = 1.0) -> None:
        """Increment a counter metric."""
        metric = getattr(self, name, None)
        if metric and isinstance(metric, Counter):
            try:
                if labels:
                    metric.labels(**labels).inc(value)
                else:
                    metric.inc(value)
                logger.debug("counter_incremented", metric_name=name, value=value, labels=labels)
            except Exception as e:
                logger.error("counter_increment_failed", metric_name=name, error=str(e))
        else:
            logger.warning("counter_not_found", metric_name=name)

    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Observe a value in a histogram metric."""
        metric = getattr(self, name, None)
        if metric and isinstance(metric, Histogram):
            try:
                if labels:
                    metric.labels(**labels).observe(value)
                else:
                    metric.observe(value)
                logger.debug("histogram_observed", metric_name=name, value=value, labels=labels)
            except Exception as e:
                logger.error("histogram_observe_failed", metric_name=name, error=str(e))
        else:
            logger.warning("histogram_not_found", metric_name=name)

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set a gauge metric value."""
        metric = getattr(self, name, None)
        if metric and isinstance(metric, Gauge):
            try:
                if labels:
                    metric.labels(**labels).set(value)
                else:
                    metric.set(value)
                logger.debug("gauge_set", metric_name=name, value=value, labels=labels)
            except Exception as e:
                logger.error("gauge_set_failed", metric_name=name, error=str(e))
        else:
            logger.warning("gauge_not_found", metric_name=name)

    def observe_summary(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Observe a value in a summary metric."""
        metric = getattr(self, name, None)
        if metric and isinstance(metric, Summary):
            try:
                if labels:
                    metric.labels(**labels).observe(value)
                else:
                    metric.observe(value)
                logger.debug("summary_observed", metric_name=name, value=value, labels=labels)
            except Exception as e:
                logger.error("summary_observe_failed", metric_name=name, error=str(e))
        else:
            logger.warning("summary_not_found", metric_name=name)

    def get_metric_value(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        """Get current value of a metric."""
        metric = getattr(self, name, None)
        if not metric:
            return None

        try:
            if isinstance(metric, Counter):
                if labels:
                    return metric.labels(**labels)._value._value
                else:
                    return metric._value._value
            elif isinstance(metric, Gauge):
                if labels:
                    return metric.labels(**labels)._value._value
                else:
                    return metric._value._value
            # For Histogram and Summary, return the sample count
            elif isinstance(metric, (Histogram, Summary)):
                if labels:
                    return metric.labels(**labels)._count._value
                else:
                    return metric._count._value
        except Exception as e:
            logger.error("get_metric_value_failed", metric_name=name, error=str(e))
            return None

    def list_metrics(self) -> List[str]:
        """List all available metrics."""
        metrics = []
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if isinstance(attr, (Counter, Histogram, Gauge, Summary)):
                metrics.append(attr_name)
        return metrics

    def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus format."""
        return generate_latest().decode('utf-8')

    def create_dynamic_counter(self, name: str, description: str, labels: List[str]) -> None:
        """Create a new counter metric dynamically."""
        if not hasattr(self, name):
            counter = Counter(name.lower(), description, labels)
            setattr(self, name, counter)
            logger.info("dynamic_counter_created", metric_name=name, labels=labels)

    def create_dynamic_histogram(self, name: str, description: str, labels: List[str], buckets: Optional[List[float]] = None) -> None:
        """Create a new histogram metric dynamically."""
        if not hasattr(self, name):
            histogram = Histogram(name.lower(), description, labels, buckets=buckets)
            setattr(self, name, histogram)
            logger.info("dynamic_histogram_created", metric_name=name, labels=labels)

    def create_dynamic_gauge(self, name: str, description: str, labels: List[str]) -> None:
        """Create a new gauge metric dynamically."""
        if not hasattr(self, name):
            gauge = Gauge(name.lower(), description, labels)
            setattr(self, name, gauge)
            logger.info("dynamic_gauge_created", metric_name=name, labels=labels)
