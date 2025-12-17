"""Prometheus metrics scaffold for notification flows."""
from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar, Optional

try:  # pragma: no cover - optional dependency
    from prometheus_client import REGISTRY, Counter
except Exception:  # pragma: no cover - fallback when prometheus_client missing
    Counter = None  # type: ignore
    REGISTRY = None  # type: ignore


@dataclass(slots=True)
class PrometheusNotificationMetrics:
    """Minimal metrics collector used during Stage A scaffolding."""

    _sent_counter: ClassVar[Optional["Counter"]] = None

    def __post_init__(self) -> None:
        if Counter is None:
            return

        if self.__class__._sent_counter is not None:
            return

        try:
            self.__class__._sent_counter = Counter(
                "notifications_sent_total",
                "Total number of notifications dispatched",
                ["channel"],
            )
        except ValueError:
            # Already registered in this process (another bootstrap). Reuse the
            # collector from the registry instead of raising.
            if REGISTRY is not None:
                for collector in REGISTRY._collector_to_names.keys():  # type: ignore[attr-defined]
                    if getattr(collector, "_name", None) == "notifications_sent_total":
                        self.__class__._sent_counter = collector  # type: ignore[assignment]
                        break
            if self.__class__._sent_counter is None:
                class _NoOpCounter:
                    def labels(self, **_kwargs):
                        class _NoOp:
                            def inc(self, _v=1):
                                return None

                        return _NoOp()

                self.__class__._sent_counter = _NoOpCounter()  # type: ignore[assignment]

    def record_notification_sent(self, channel: str) -> None:
        if self._sent_counter is not None:
            self._sent_counter.labels(channel=channel).inc()


__all__ = ["PrometheusNotificationMetrics"]
