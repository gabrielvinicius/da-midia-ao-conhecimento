"""Media management metrics wired to shared Prometheus registry."""

from __future__ import annotations

from typing import Any

from src.shared.infrastructure.prometheus_metrics import shared_metrics


class PrometheusMediaMetrics:
    """Prometheus-backed metrics recorder for media management operations."""

    def __init__(self) -> None:
        self._operations_total = shared_metrics.get_media_management_operations_total()
        self._operation_duration = shared_metrics.get_media_management_operation_duration_seconds()

    async def record_operation(
        self,
        *,
        operation: str,
        user_id: str,
        media_type: str,
        provider: str | None,
        status: str,
        duration: float,
        media_id: str | None = None,
        file_size_bytes: int | None = None,
    ) -> None:
        provider = provider or "unknown"
        media_id = media_id or "unknown"
        self._operations_total.labels(
            operation=operation,
            provider=provider,
            status=status,
            media_id=media_id,
            user_id=user_id,
            media_type=media_type,
        ).inc()
        self._operation_duration.labels(
            operation=operation,
            provider=provider,
            status=status,
            media_id=media_id,
            user_id=user_id,
            media_type=media_type,
        ).observe(duration)


class NoOpMediaMetrics:
    async def record_operation(self, **_: Any) -> None:
        return None


__all__ = ["PrometheusMediaMetrics", "NoOpMediaMetrics"]
