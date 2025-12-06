"""Metrics collectors for video processing workflows."""
from __future__ import annotations

from prometheus_client import Counter, Histogram

from src.shared.infrastructure.metrics import shared_metrics


class PrometheusVideoProcessingMetrics:
    """Prometheus-backed metrics recorder for video processing operations.
    Uses shared metrics to prevent duplicate registration in Celery workers.
    """

    def __init__(self) -> None:
        # Use shared metrics to prevent duplicate registration
        self._operations_total = shared_metrics.get_video_processing_operations_total()
        self._operation_duration = shared_metrics.get_video_processing_duration_seconds()
        self._file_size_bytes = shared_metrics.get_video_processing_input_file_size_bytes()

    async def record_operation(
        self,
        *,
        operation: str,
        duration: float,
        success: bool,
        file_size_bytes: int,
    ) -> None:
        status = 'success' if success else 'failure'
        self._operations_total.labels(operation=operation, status=status).inc()
        self._operation_duration.labels(operation=operation).observe(duration)
        if success:
            self._file_size_bytes.labels(operation=operation).observe(file_size_bytes)


class NoOpVideoProcessingMetrics:
    """No-op metrics implementation used when metrics collection is disabled."""

    async def record_operation(
        self,
        *,
        operation: str,
        duration: float,
        success: bool,
        file_size_bytes: int,
    ) -> None:
        return