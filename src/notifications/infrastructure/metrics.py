"""Prometheus metrics scaffold for notification flows."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

try:  # pragma: no cover - optional dependency
    from prometheus_client import Counter
except Exception:  # pragma: no cover - fallback when prometheus_client missing
    Counter = None  # type: ignore


@dataclass(slots=True)
class PrometheusNotificationMetrics:
    """Minimal metrics collector used during Stage A scaffolding."""

    _sent_counter: Optional["Counter"] = None

    def __post_init__(self) -> None:
        if Counter is not None:
            self._sent_counter = Counter(
                "notifications_sent_total",
                "Total number of notifications dispatched",
                ["channel"],
            )

    def record_notification_sent(self, channel: str) -> None:
        if self._sent_counter is not None:
            self._sent_counter.labels(channel=channel).inc()


__all__ = ["PrometheusNotificationMetrics"]
