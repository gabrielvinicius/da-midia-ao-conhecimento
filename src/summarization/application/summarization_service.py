# src/summarization/application/summarization_service.py
"""High level orchestration for summary creation and retrieval."""

from __future__ import annotations

from typing import Optional, Any, Dict
from uuid import UUID

from src.summarization.domain.summary import Summary
from src.summarization.infrastructure.summarization_repository import SummarizationRepository
from src.summarization.infrastructure.summarizer import TextRankSummarizer
from src.summarization.infrastructure.task_scheduler import CelerySummarizationTaskScheduler

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
        summarization_task_scheduler: CelerySummarizationTaskScheduler,
    ) -> None:
        self._repo = summarization_repo
        self._summarizer = summarizer
        self._task_scheduler = summarization_task_scheduler

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
        task_result = await self._task_scheduler.schedule_summarization_task(
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
