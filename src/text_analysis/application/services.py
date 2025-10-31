"""Placeholder service definitions for the text analysis module."""
from __future__ import annotations

from typing import Any, Optional

from src.shared.events.domain_events import TextContentReady


class TextAnalysisService:
    """Facade responsible for coordinating text analysis workflows."""

    async def generate_text_artifacts(
        self,
        media_id: str,
        *,
        options: Optional[dict[str, Any]] = None,
    ) -> TextContentReady:
        """Produce summaries, topics and sentiment results (Stage F implementation)."""

        raise NotImplementedError("Stage F will implement the text analysis orchestration.")


__all__ = ["TextAnalysisService"]
