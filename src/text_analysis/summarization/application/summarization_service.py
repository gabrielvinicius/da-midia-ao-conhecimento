# src/summarization/application/summarization_service.py
"""High level orchestration for summary creation and retrieval."""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from src.text_analysis.application.services import TextAnalysisService  # New import
from src.text_analysis.summarization.domain.summary import Summary
from src.text_analysis.summarization.infrastructure.summarization_repository import (
    SummarizationRepository,
)
from src.text_analysis.summarization.infrastructure.summarizer import TextRankSummarizer


def _ensure_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


class SummarizationService:
    """Coordinates summarisation requests without background infrastructure."""

    def __init__(
        self,
        *,
        summarization_repo: SummarizationRepository,
        summarizer: TextRankSummarizer,
        text_analysis_service: TextAnalysisService, # Injected TextAnalysisService
    ) -> None:
        self._repo = summarization_repo
        self._summarizer = summarizer
        self._text_analysis_service = text_analysis_service # Store the injected service

    async def generate_summary(
        self,
        *,
        media_id: UUID | str,
        text_content: str,
        provider: str = "builtin",
        options: Optional[dict[str, object]] = None,
    ) -> Dict[str, Any]:
        """Requests the generation of a summary for the supplied media by scheduling a task."""
        media_uuid = _ensure_uuid(media_id)
        task_result = await self._text_analysis_service.schedule_summarization_task(
            media_id=str(media_uuid),
            text_content=text_content,
            provider=provider,
            options=options
        )
        return {
            "success": True,
            "media_id": str(media_uuid),
            "task_id": task_result.get("task_id"),
            "message": "Summarization task scheduled successfully"
        }

    async def get_summary_by_media_id(self, media_id: UUID | str) -> Optional[Summary]:
        """Retrieve the latest summary linked to the provided media identifier."""
        return await self._repo.get_by_media_id(_ensure_uuid(media_id))

    async def get_summary_by_id(self, summary_id: UUID | str) -> Optional[Summary]:
        """Retrieve a summary by its identifier."""
        return await self._repo.get_by_id(_ensure_uuid(summary_id))
