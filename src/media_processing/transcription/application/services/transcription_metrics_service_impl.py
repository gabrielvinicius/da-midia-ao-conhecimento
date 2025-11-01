"""Metrics implementation for transcription workflows."""
from __future__ import annotations

from typing import Any, Dict


class TranscriptionMetricsServiceImpl:
    def __init__(self, metrics_collector: Any) -> None:
        self._collector = metrics_collector

    def record_transcription(self, *, success: bool, duration: float) -> None:
        payload: Dict[str, float | bool] = {
            "success": success,
            "duration": duration,
        }
        record = getattr(self._collector, "record", None)
        if callable(record):
            record("transcription_generated", payload)
