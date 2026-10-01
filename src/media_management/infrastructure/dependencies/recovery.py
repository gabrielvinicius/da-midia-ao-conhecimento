"""Montagem da recuperação de mídias que não começaram a ser processadas."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.application.ports import EventBusPort
from src.media_management.application.services.unstarted_media_recovery import (
    UnstartedMediaRecovery,
)
from src.media_management.config.settings import media_settings
from src.media_management.infrastructure.repositories.media_repository import MediaRepository
from src.media_processing.infrastructure.adapters.processing_records_adapter import (
    ProcessingRecordsAdapter,
)
from src.media_processing.infrastructure.repositories.transcription_repository import (
    TranscriptionRepository,
)


def build_unstarted_media_recovery(
    session: AsyncSession, event_bus: EventBusPort
) -> UnstartedMediaRecovery:
    return UnstartedMediaRecovery(
        media=MediaRepository(db=session),
        processing=ProcessingRecordsAdapter(TranscriptionRepository(db=session)),
        event_bus=event_bus,
        grace_seconds=media_settings.unstarted_grace_minutes * 60,
        give_up_seconds=media_settings.unstarted_give_up_minutes * 60,
    )


__all__ = ["build_unstarted_media_recovery"]
