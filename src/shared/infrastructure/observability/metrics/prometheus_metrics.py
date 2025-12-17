"""Module for managing shared Prometheus metrics across different contexts
(FastAPI and Celery) to avoid metric duplication.
"""
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
            ["operation", "provider", "media_id", "status"],
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
            Gauge,
        )

    # --- Metrics for Video Processing ---
    def get_video_processing_operations_total(self) -> Counter:
        return self._get_or_create_metric(
            "counter",
            "video_processing_operations_total",
            "Total number of video processing operations",
            ["operation", "status"],
            Counter,
        )

    def get_video_processing_duration_seconds(self) -> Histogram:
        return self._get_or_create_metric(
            "histogram",
            "video_processing_operation_duration_seconds",
            "Duration of video processing operations",
            ["operation"],
            Histogram,
        )

    def get_video_processing_input_file_size_bytes(self) -> Histogram:
        return self._get_or_create_metric(
            "histogram",
            "video_processing_input_file_size_bytes",
            "Size of video files processed",
            ["operation"],
            Histogram,
        )

    # --- Metrics for Text Analysis ---
    def get_text_analysis_operations_total(self) -> Counter:
        return self._get_or_create_metric(
            "counter",
            "text_analysis_operations_total",
            "Total number of text analysis operations",
            ["operation", "provider", "status", "media_id", "user_id"],
            Counter,
        )

    def get_text_analysis_duration_seconds(self) -> Histogram:
        return self._get_or_create_metric(
            "histogram",
            "text_analysis_operation_duration_seconds",
            "Duration of text analysis operations in seconds",
            ["operation", "provider", "media_id", "user_id", "status"],
            Histogram,
        )

    # --- Metrics for Topic Modeling ---
    def get_topic_modeling_operations_total(self) -> Counter:
        return self._get_or_create_metric(
            "counter",
            "topic_modeling_operations_total",
            "Total number of topic modeling operations",
            ["operation", "provider", "status"],
            Counter,
        )

    def get_topic_modeling_operation_duration_seconds(self) -> Histogram:
        return self._get_or_create_metric(
            "histogram",
            "topic_modeling_operation_duration_seconds",
            "Duration of topic modeling operations in seconds",
            ["operation", "provider"],
            Histogram,
        )

    def get_topic_modeling_input_text_length_chars(self) -> Histogram:
        return self._get_or_create_metric(
            "histogram",
            "topic_modeling_input_text_length_chars",
            "Length of input text in characters",
            ["provider"],
            Histogram,
        )

    def get_topic_modeling_num_topics(self) -> Histogram:
        return self._get_or_create_metric(
            "histogram",
            "topic_modeling_num_topics",
            "Number of topics identified",
            ["provider"],
            Histogram,
        )

    def get_topic_modeling_active_operations(self) -> Gauge:
        return self._get_or_create_metric(
            "gauge",
            "topic_modeling_active_operations",
            "Number of active topic modeling operations",
            ["provider"],
            Gauge,
        )

    # --- Metrics for Sentiment Analysis ---
    def get_sentiment_analysis_events_total(self) -> Counter:
        return self._get_or_create_metric(
            "counter",
            "sentiment_analysis_events_total",
            "Total number of sentiment analysis events emitted.",
            ("metric",),
            Counter,
        )

    def get_sentiment_analysis_processing_seconds(self) -> Histogram:
        return self._get_or_create_metric(
            "histogram",
            "sentiment_analysis_processing_seconds",
            "Observed processing time for sentiment analysis operations.",
            ("metric",),
            Histogram,
        )

    # --- Metrics for Text Processing (OCR/Extraction) ---
    def get_text_processing_operations_total(self) -> Counter:
        return self._get_or_create_metric(
            "counter",
            "text_processing_operations_total",
            "Total number of text processing operations",
            ["operation", "format_type", "status"],
            Counter,
        )

    def get_text_processing_operation_duration_seconds(self) -> Histogram:
        return self._get_or_create_metric(
            "histogram",
            "text_processing_operation_duration_seconds",
            "Duration of text processing operations in seconds",
            ["operation", "format_type"],
            Histogram,
        )

    def get_text_processing_file_size_bytes(self) -> Histogram:
        return self._get_or_create_metric(
            "histogram",
            "text_processing_file_size_bytes",
            "Size of processed files in bytes",
            ["format_type"],
            Histogram,
        )

    def get_text_processing_text_length_chars(self) -> Histogram:
        return self._get_or_create_metric(
            "histogram",
            "text_processing_text_length_chars",
            "Length of extracted text in characters",
            ["format_type"],
            Histogram,
        )

    def get_text_processing_extraction_ratio(self) -> Histogram:
        return self._get_or_create_metric(
            "histogram",
            "text_processing_extraction_ratio",
            "Ratio of extracted text length to file size",
            ["format_type"],
            Histogram,
        )

    def get_text_processing_active_operations(self) -> Gauge:
        return self._get_or_create_metric(
            "gauge",
            "text_processing_active_operations",
            "Number of active text processing operations",
            ["format_type"],
            Gauge,
        )


# Global shared instance
shared_metrics = SharedPrometheusMetrics()
