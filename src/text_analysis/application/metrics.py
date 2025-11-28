"""Lightweight metrics hook for text analysis operations."""

from __future__ import annotations

from typing import Protocol


class TextAnalysisMetrics(Protocol):
    async def record_operation(
        self,
        *,
        operation: str,
        duration: float,
        success: bool,
        provider: str | None = None,
    ) -> None:  # pragma: no cover - interface
        ...


class NoOpTextAnalysisMetrics:
    async def record_operation(self, **_kwargs) -> None:  # pragma: no cover
        return None


__all__ = ["TextAnalysisMetrics", "NoOpTextAnalysisMetrics"]
