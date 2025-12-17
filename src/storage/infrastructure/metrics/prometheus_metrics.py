# src/storage/infrastructure/metrics.py
"""Storage metrics implementation - SRP compliance.
"""
from typing import Any, Dict

from prometheus_client import Counter, Gauge, Histogram

from src.storage.application.ports import StorageMetricsPort


class PrometheusStorageMetrics(StorageMetricsPort):
    """Prometheus-based metrics implementation for storage operations.
    Follows SRP - only responsible for metrics collection.
    """

    def __init__(self):
        # Operation counters
        self._operation_counter = Counter(
            'storage_operations_total',
            'Total number of storage operations',
            ['operation', 'provider', 'status']
        )

        # Operation duration histogram
        self._operation_duration = Histogram(
            'storage_operation_duration_seconds',
            'Duration of storage operations in seconds',
            ['operation', 'provider']
        )

        # Active operations gauge
        self._active_operations = Gauge(
            'storage_active_operations',
            'Number of active storage operations',
            ['operation', 'provider']
        )

    async def record_operation(
        self,
        operation: str,
        provider: str,
        duration: float,
        success: bool
    ) -> None:
        """Record storage operation metrics."""
        status = "success" if success else "failure"

        # Increment operation counter
        self._operation_counter.labels(
            operation=operation,
            provider=provider,
            status=status
        ).inc()

        # Record operation duration
        self._operation_duration.labels(
            operation=operation,
            provider=provider
        ).observe(duration)


class InMemoryStorageMetrics(StorageMetricsPort):
    """In-memory metrics implementation for testing.
    Follows SRP and provides same interface.
    """

    def __init__(self):
        self._metrics: Dict[str, Dict[str, Any]] = {}

    async def record_operation(
        self,
        operation: str,
        provider: str,
        duration: float,
        success: bool
    ) -> None:
        """Record operation metrics in memory."""
        key = f"{operation}_{provider}"

        if key not in self._metrics:
            self._metrics[key] = {
                "total_operations": 0,
                "successful_operations": 0,
                "failed_operations": 0,
                "total_duration": 0.0,
                "min_duration": float('inf'),
                "max_duration": 0.0
            }

        metrics = self._metrics[key]
        metrics["total_operations"] += 1
        metrics["total_duration"] += duration
        metrics["min_duration"] = min(metrics["min_duration"], duration)
        metrics["max_duration"] = max(metrics["max_duration"], duration)

        if success:
            metrics["successful_operations"] += 1
        else:
            metrics["failed_operations"] += 1

    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get all recorded metrics (for testing)."""
        return self._metrics.copy()

    def reset_metrics(self) -> None:
        """Reset all metrics (for testing)."""
        self._metrics.clear()


class NoOpStorageMetrics(StorageMetricsPort):
    """No-operation metrics for when metrics are disabled.
    Follows Null Object pattern.
    """

    async def record_operation(
        self,
        operation: str,
        provider: str,
        duration: float,
        success: bool
    ) -> None:
        """No-op implementation."""
        pass
