from __future__ import annotations

from typing import Optional
from uuid import UUID

from src.media_processing.infrastructure.repositories.transcription_repository import (
    TranscriptionRepository,
)
from src.text_analysis.application.ports.transcription_port import (
    TextSourceData,
    TranscriptionQueryPort,
)


class TranscriptionQueryAdapter(TranscriptionQueryPort):
    """Expose transcription queries to text_analysis via media_processing repo."""

    def __init__(self, repo: TranscriptionRepository):
        self._repo = repo

    async def get_text_source(self, media_id: UUID) -> Optional[TextSourceData]:
        """Retrieves standardized text source data for a given media ID."""
        transcription = await self._repo.get_by_media_id(media_id)
        if not transcription:
            return None

        # Prioritize 'text' field, fallback to 'content' if legacy
        text_content = getattr(transcription, "text", "") or getattr(
            transcription, "content", ""
        )

        return TextSourceData(
            id=transcription.id,
            text=text_content,
            language=transcription.language or "auto",
            segments=transcription.segments or [],
            media_id=transcription.media_id,
        )


__all__ = ["TranscriptionQueryAdapter"]