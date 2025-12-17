from __future__ import annotations

from src.notifications.application.ports import NotificationMetricsPort
from src.notifications.infrastructure.metrics.prometheus_metrics import (
    PrometheusNotificationMetrics,
)
from src.shared.infrastructure.config.settings import settings


class NotificationMetricsAdapter(NotificationMetricsPort):
    """Adapter that wraps PrometheusNotificationMetrics into the async port."""

    def __init__(self, metrics: PrometheusNotificationMetrics | None = None) -> None:
        if metrics is not None:
            self._metrics = metrics
        elif settings.LIGHTWEIGHT_BOOTSTRAP:
            # Avoid Prometheus collector registration in lightweight/test mode.
            self._metrics = _NoOpNotificationMetrics()
        else:
            self._metrics = PrometheusNotificationMetrics()

    async def record_operation(self, **kwargs):
        # Keep compatibility with SharedMetricsPort shape; no-op for now.
        return None

    def set_context(self, *args, **kwargs):
        return None

    async def record_notification_sent(self, channel: str) -> None:
        self._metrics.record_notification_sent(channel)


class _NoOpNotificationMetrics(PrometheusNotificationMetrics):
    """No-op metrics used to prevent duplicate Prometheus collectors in tests."""

    def __post_init__(self) -> None:  # pragma: no cover - trivial
        return

    def record_notification_sent(self, channel: str) -> None:
        return


__all__ = ["NotificationMetricsAdapter"]
