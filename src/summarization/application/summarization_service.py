# src/summarization/application/summarization_service.py
"""High level orchestration for summary creation and retrieval."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from src.summarization.domain.summary import Summary
from src.summarization.infrastructure.summarization_repository import SummarizationRepository
from src.summarization.infrastructure.summarizer import TextRankSummarizer


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
    ) -> None:
        self._repo = summarization_repo
        self._summarizer = summarizer

    async def generate_summary(
        self,
        *,
        media_id: UUID | str,
        text_content: str,
        provider: str = "builtin",
        options: Optional[dict[str, object]] = None,
    ) -> Summary:
        """Create or update a summary for the supplied media."""

        media_uuid = _ensure_uuid(media_id)
        existing = await self._repo.get_by_media_id(media_uuid)

        summary = (
            existing.with_provider(provider).mark_processing()
            if existing
            else Summary.create(media_id=media_uuid, provider=provider)
        )

        if existing is None:
            summary = await self._repo.add(summary)

        summary_text = await self._summarizer.summarize(text_content, options)
        completed = summary.mark_as_completed(summary_text)
        return await self._repo.update(completed)

    async def mark_failure(
        self,
        *,
        media_id: UUID | str,
        error_message: str,
        provider: str = "builtin",
    ) -> Summary:
        """Persist a failure state for a summary."""

        media_uuid = _ensure_uuid(media_id)
        summary = await self._repo.get_by_media_id(media_uuid)

        if summary is None:
            summary = Summary.create(media_id=media_uuid, provider=provider)
            summary = await self._repo.add(summary)

        failed = summary.mark_as_failed(error_message)
        return await self._repo.update(failed)

    async def get_summary_by_media_id(self, media_id: UUID | str) -> Optional[Summary]:
        return await self._repo.get_by_media_id(_ensure_uuid(media_id))

    async def get_summary_by_id(self, summary_id: UUID | str) -> Optional[Summary]:
        return await self._repo.get_by_id(_ensure_uuid(summary_id))

    async def delete_summary(self, media_id: UUID | str) -> None:
        await self._repo.delete_by_media_id(_ensure_uuid(media_id))
