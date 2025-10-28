"""Transcription event handlers."""

import logging
from typing import Any, Optional, Protocol

from src.media_management.domain.media import MediaType
from src.media_management.application.queries.media_queries import MediaQueries
from src.shared.events.domain_events import AudioExtracted, MediaDeleted, MediaUploaded
from src.shared.events.event_bus import EventBus
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository


logger = logging.getLogger(__name__)

DEFAULT_TRANSCRIPTION_PROVIDER = "whisper"


class _TranscriptionTask(Protocol):
    """Protocol describing the Celery task signature used by the handlers."""

    def delay(
        self,
        *,
        media_id: str,
        file_path: str,
        storage_provider: str,
        transcription_provider: str,
        language: str = "en",
    ) -> Any:
        ...


def _load_default_task() -> "_TranscriptionTask":
    from src.transcription.tasks.tasks import process_transcription_task

    return process_transcription_task


async def register_event_handlers(
    event_bus: EventBus,
    transcription_repository: TranscriptionRepository,
    media_queries: MediaQueries,
    transcription_task: Optional[_TranscriptionTask] = None,
) -> None:
    """Register transcription handlers with the event bus."""

    if transcription_task is None:
        transcription_task = _load_default_task()

    async def handle_media_uploaded(event: MediaUploaded) -> None:
        try:
            if event.media_type != MediaType.AUDIO:
                return

            media = await media_queries.get_by_id(event.media_id)
            if not media:
                logger.warning("Media %s not found during transcription scheduling", event.media_id)
                return

            provider = (
                event.transcription_provider
                or getattr(media, "transcription_provider", None)
                or DEFAULT_TRANSCRIPTION_PROVIDER
            )
            file_path = getattr(media, "original_file_path", event.file_path)
            storage_provider = getattr(media, "storage_provider", event.storage_provider)
            language = getattr(media, "language", None) or "en"

            transcription_task.delay(
                media_id=event.media_id,
                file_path=file_path,
                storage_provider=storage_provider,
                transcription_provider=provider,
                language=language,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to handle MediaUploaded event for transcription: %s",
                exc,
                exc_info=True,
            )

    async def handle_audio_extracted(event: AudioExtracted) -> None:
        try:
            media = await media_queries.get_by_id(event.media_id)
            if not media:
                logger.warning(
                    "Media %s not found during audio extracted handling", event.media_id
                )
                return

            provider = (
                event.transcription_provider
                or getattr(media, "transcription_provider", None)
                or DEFAULT_TRANSCRIPTION_PROVIDER
            )
            language = getattr(media, "language", None) or "en"
            storage_provider = event.storage_provider or getattr(media, "storage_provider", event.storage_provider)

            transcription_task.delay(
                media_id=event.media_id,
                file_path=event.audio_file_path,
                storage_provider=storage_provider,
                transcription_provider=provider,
                language=language,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to handle AudioExtracted event: %s",
                exc,
                exc_info=True,
            )

    async def handle_media_deleted(event: MediaDeleted) -> None:
        try:
            await transcription_repository.delete_by_media_id(event.media_id)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "Failed to handle MediaDeleted event for transcription: %s",
                exc,
                exc_info=True,
            )

    event_bus.subscribe(MediaUploaded, handle_media_uploaded)
    event_bus.subscribe(AudioExtracted, handle_audio_extracted)
    event_bus.subscribe(MediaDeleted, handle_media_deleted)


__all__ = ["register_event_handlers"]
