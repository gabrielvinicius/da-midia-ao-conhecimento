"""Prometheus metrics implementation for media management."""

from typing import Optional

from src.shared.infrastructure.observability.metrics.prometheus_metrics import shared_metrics


class PrometheusMediaMetrics:
    """Metrics wrapper for Media Management."""

    def __init__(self) -> None:
        self._operations_total = shared_metrics.get_media_operations_total()
        self._duration_seconds = shared_metrics.get_media_duration_seconds()

    async def record_operation(
        self,
        *,
        operation: str,
        duration: float,
        success: bool,
        media_id: Optional[str] = None,
        media_type: Optional[str] = None,
        provider: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None, # sometimes passed explicitly
    ) -> None:
        status_label = status or ("success" if success else "failure")
        provider_label = provider or "unknown"
        media_id_label = media_id or "unknown"
        
        self._operations_total.labels(
            operation=operation,
            provider=provider_label,
            status=status_label,
            media_id=media_id_label
        ).inc()
        
        self._duration_seconds.labels(
            operation=operation,
            provider=provider_label,
            media_id=media_id_label,
            status=status_label
        ).observe(duration)
