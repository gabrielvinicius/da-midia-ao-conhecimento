from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from src.media_processing.domain.visual_sampling import VISUAL_CONTEXT_KEY
from src.media_processing.infrastructure.repositories.transcription_repository import (
    TranscriptionRepository,
)
from src.media_management.infrastructure.repositories.media_repository import (
    MediaRepository,
)
from src.text_analysis.application.ports.transcription_port import (
    TextSourceData,
    TranscriptionQueryPort,
)


class TranscriptionQueryAdapter(TranscriptionQueryPort):
    """Expose transcription queries to text_analysis via media_processing repo."""

    def __init__(self, repo: TranscriptionRepository, media_repo: Optional[MediaRepository] = None):
        self._repo = repo
        self._media_repo = media_repo

    async def get_text_source(self, media_id: UUID) -> Optional[TextSourceData]:
        # ... exists ...
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
            visual_context=list((transcription.result or {}).get(VISUAL_CONTEXT_KEY) or []),
        )

    async def get_media_info(self, media_id: UUID) -> Optional[Dict[str, Any]]:
        """Retrieves media metadata (file_path, storage_provider, type)."""
        if not self._media_repo:
            return None
            
        media = await self._media_repo.get_by_id(media_id)
        if not media:
            return None
            
        return {
            "file_path": media.original_file_path,
            "storage_provider": media.storage_provider,
            "media_type": media.media_type
        }



__all__ = ["TranscriptionQueryAdapter"]