"""Metrics collectors for video processing workflows."""
from __future__ import annotations

from prometheus_client import Counter, Histogram


class PrometheusVideoProcessingMetrics:
    """Prometheus-backed metrics recorder for video processing operations."""

    def __init__(self) -> None:
        self._operations_total = Counter(
            'video_processing_operations_total',
            'Total number of video processing operations',
            ['operation', 'status'],
        )
        self._operation_duration = Histogram(
            'video_processing_operation_duration_seconds',
            'Duration of video processing operations',
            ['operation'],
        )
        self._file_size_bytes = Histogram(
            'video_processing_input_file_size_bytes',
            'Size of video files processed',
            ['operation'],
        )

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
