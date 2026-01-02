"""Prometheus metrics implementation for media management."""

from typing import Optional

from src.shared.infrastructure.observability.metrics.prometheus_metrics import (
    shared_metrics,
)


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
        success: bool | None = None,
        media_id: Optional[str] = None,
        media_type: Optional[str] = None,
        provider: Optional[str] = None,
        user_id: Optional[str] = None,
        status: Optional[str] = None, # sometimes passed explicitly
    ) -> None:
        if success is None and status is None:
            # se vier sem sucesso, assume failure defensiva
            success = False
        status_label = status or ("success" if success else "failure")
        provider_label = provider or "unknown"
        media_id_label = media_id or "unknown"

        # Standard order: operation, provider, status, media_id
        labels = (operation, provider_label, status_label, media_id_label)

        try:
            self._operations_total.labels(*labels).inc()
            self._duration_seconds.labels(*labels).observe(duration)
        except ValueError:
            # defensive catch if REGISTRY has old label set
            pass
