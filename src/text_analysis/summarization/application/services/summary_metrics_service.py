"""Metrics recording utilities for summarization workflows."""
from __future__ import annotations

from typing import Any, Dict


class SummaryMetricsService:
    """Simple abstraction over the monitoring collector used in tests."""

    def __init__(self, metrics_collector: Any) -> None:
        self._collector = metrics_collector

    def record_summary(self, *, success: bool, duration: float) -> None:
        payload: Dict[str, float | bool] = {
            "success": success,
            "duration": duration,
        }
        record = getattr(self._collector, "record", None)
        if callable(record):
            record("summary_generated", payload)

