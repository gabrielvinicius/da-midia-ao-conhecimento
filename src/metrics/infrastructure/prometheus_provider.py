# src/metrics/infrastructure/prometheus_provider.py
from prometheus_client import Counter, Histogram
from src.metrics.domain.metrics import MetricsProvider

class PrometheusMetricsProvider(MetricsProvider):
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

    def increment_counter(self, name: str, labels: dict = None):
        metric = getattr(self, name, None)
        if metric and isinstance(metric, Counter):
            if labels:
                metric.labels(**labels).inc()
            else:
                metric.inc()

    def observe_histogram(self, name: str, value: float, labels: dict = None):
        metric = getattr(self, name, None)
        if metric and isinstance(metric, Histogram):
            if labels:
                metric.labels(**labels).observe(value)
            else:
                metric.observe(value)
