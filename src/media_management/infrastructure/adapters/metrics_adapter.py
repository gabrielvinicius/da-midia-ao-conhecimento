from __future__ import annotations

from src.media_management.application.ports import MediaMetricsPort
from src.media_management.infrastructure.metrics.prometheus_metrics import (
    PrometheusMediaMetrics,
)


class MediaMetricsAdapter(MediaMetricsPort):
    def __init__(self, impl: PrometheusMediaMetrics | None = None) -> None:
        self._impl = impl or PrometheusMediaMetrics()

    async def record_operation(self, **kwargs):
        return await self._impl.record_operation(**kwargs)

    def set_context(self, *args, **kwargs):
        if hasattr(self._impl, "set_context"):
            return self._impl.set_context(*args, **kwargs)
        return None


__all__ = ["MediaMetricsAdapter"]
