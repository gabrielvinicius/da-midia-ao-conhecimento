"""Estados da mídia conduzidos pelos eventos do processamento."""
from __future__ import annotations

import uuid
from typing import Callable, Optional

import structlog

from src.media_management.application.ports import MediaRepositoryPort
from src.media_management.domain import Media

logger = structlog.get_logger(__name__)


class MediaLifecycle:
    def __init__(self, media_repository: MediaRepositoryPort) -> None:
        self._media = media_repository

    async def record_processing_started(self, media_id: uuid.UUID) -> Optional[Media]:
        return await self._transition(media_id, lambda media: media.mark_as_processing())

    async def record_text_ready(self, media_id: uuid.UUID) -> Optional[Media]:
        return await self._transition(media_id, lambda media: media.mark_as_completed())

    async def record_processing_failed(
        self, media_id: uuid.UUID, error_message: Optional[str]
    ) -> Optional[Media]:
        return await self._transition(
            media_id, lambda media: media.mark_as_failed(error_message or "Erro desconhecido")
        )

    async def _transition(self, media_id: uuid.UUID, change: Callable[[Media], None]) -> Optional[Media]:
        """Carrega a mídia, aplica a regra da entidade e grava. None se não existir."""
        media = await self._media.get_by_id(media_id)
        if not media:
            logger.error("media_management.media_not_found", media_id=str(media_id))
            return None
        change(media)
        await self._media.update(media)
        return media
