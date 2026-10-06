from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

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
        transcription = await self._repo.get_by_media_id(media_id)
        if not transcription:
            return None

        return TextSourceData(
            id=transcription.id,
            text=transcription.text,
            language=transcription.language or "auto",
            segments=transcription.segments or [],
            media_id=transcription.media_id,
            visual_context=list(transcription.visual_context),
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


    async def get_media_owner(self, media_id: UUID) -> Optional[UUID]:
        if not self._media_repo:
            return None
        media = await self._media_repo.get_by_id(media_id)
        return media.user_id if media else None


__all__ = ["TranscriptionQueryAdapter"]