"""Module for managing shared Prometheus metrics across different contexts
(FastAPI and Celery) to avoid metric duplication.
"""
from functools import partial
from threading import Lock
from typing import Any, Dict, List, Optional

from prometheus_client import REGISTRY, Counter, Gauge, Histogram


class SharedPrometheusMetrics:
    """Singleton for managing Prometheus metrics that can be shared
    between different contexts (API and Celery) to avoid duplication.
    """

    _instance: Optional['SharedPrometheusMetrics'] = None
    _lock = Lock()
    _initialized = False

    # Dictionaries to store already registered metrics
    _counters: Dict[str, Counter] = {}
    _histograms: Dict[str, Histogram] = {}
    _gauges: Dict[str, Gauge] = {}

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None: # Double-check inside lock
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False # Initialize state here
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        with self._lock:
            if self._initialized: # Double-check inside lock
                return
            self._initialized = True

    def _get_or_create_metric(
        self,
        metric_type: str,
        name: str,
        doc: str,
        labels: List[str],
        cls_type: Any,
    ) -> Any:
        metrics_dict = getattr(self, f"_{metric_type}s")
        if name not in metrics_dict:
            try:
                metrics_dict[name] = cls_type(name, doc, labels)
            except ValueError:
                # Metric already registered by another part of the application
                # (e.g., Celery)
                # Retrieve it from the registry
                for collector in REGISTRY._collector_to_names.keys():
                    if getattr(collector, '_name', None) == name:
                        metrics_dict[name] = collector
                        break
                else:
                    # Fallback to a no-op metric if not found
                    # (shouldn't happen in a well-behaved app)
                    class NoOpMetric:
                        def labels(self, **_labels):
                            class NoOpSubMetric:
                                def inc(self, _v=1): pass
                                def dec(self, _v=1): pass
                                def observe(self, _v): pass
                                def set(self, _v): pass
                            return NoOpSubMetric()
                    metrics_dict[name] = NoOpMetric()
        return metrics_dict[name]

    # --- Metrics for Media Operations ---
    def get_media_operations_total(self) -> Counter:
        return self._get_or_create_metric(
            "counter", 'media_operations_total', 'Total number of media operations',
            ['operation', 'provider', 'status', 'media_id'], Counter
        )

    def get_media_duration_seconds(self) -> Histogram:
        return self._get_or_create_metric(
            "histogram",
            "media_operation_duration_seconds",
            "Duration of media operations in seconds",
            ["operation", "provider", "status", "media_id"],
            Histogram,
        )

    # --- Metrics for Transcription ---
    def get_transcription_operation_counter(self) -> Counter:
        return self._get_or_create_metric(
            "counter",
            "transcription_operations_total",
            "Total number of transcription operations",
            ["operation", "provider", "status"],
            Counter,
        )

    def get_transcription_operation_duration(self) -> Histogram:
        return self._get_or_create_metric(
            "histogram",
            "transcription_operation_duration_seconds",
            "Duration of transcription operations in seconds",
            ["operation", "provider"],
            Histogram,
        )

    def get_transcription_input_audio_length(self) -> Histogram:
        return self._get_or_create_metric(
            "histogram",
            "transcription_input_audio_length_seconds",
            "Length of input audio in seconds",
            ["provider"],
            Histogram,
        )

    def get_transcription_output_text_length(self) -> Histogram:
        return self._get_or_create_metric(
            "histogram",
            "transcription_output_text_length_chars",
            "Length of output text in characters",
            ["provider"],
            Histogram,
        )

    def get_transcription_active_operations(self) -> Gauge:
        return self._get_or_create_metric(
            "gauge",
            "transcription_active_operations",
            "Number of active transcription operations",
            ["provider"],
            partial(Gauge, multiprocess_mode="livesum"),
        )

    # --- Metrics for Text Analysis ---
    def get_text_analysis_operations_total(self) -> Counter:
        return self._get_or_create_metric(
            "counter",
            "text_analysis_operations_total",
            "Total number of text analysis operations",
            ["operation", "provider", "status", "media_id", "user_id"],
            Counter
        )

    def get_text_analysis_duration_seconds(self) -> Histogram:
        return self._get_or_create_metric(
            "histogram",
            "text_analysis_operation_duration_seconds",
            "Duration of text analysis operations in seconds",
            ["operation", "provider", "status", "media_id", "user_id"],
            Histogram,
        )

    # --- Health / Providers ---
    def get_provider_health_checks_total(self) -> Counter:
        return self._get_or_create_metric(
            "counter",
            "provider_health_checks_total",
            "Total provider health checks",
            ["provider_type", "status"],
            Counter,
        )

    def get_textgen_ollama_attempts(self) -> Counter:
        return self._get_or_create_metric(
            "counter",
            "textgen_ollama_attempts_total",
            "Ollama text generation attempts",
            ["model"],
            Counter,
        )

    def get_textgen_ollama_failures(self) -> Counter:
        return self._get_or_create_metric(
            "counter",
            "textgen_ollama_failures_total",
            "Ollama text generation failures",
            ["model"],
            Counter,
        )

    def get_textgen_ollama_retries(self) -> Counter:
        return self._get_or_create_metric(
            "counter",
            "textgen_ollama_retries_total",
            "Ollama text generation retries",
            ["model"],
            Counter,
        )


# Global shared instance
shared_metrics = SharedPrometheusMetrics()
