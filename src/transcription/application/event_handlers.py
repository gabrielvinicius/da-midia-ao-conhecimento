# src/transcription/application/event_handlers.py
import logging
from typing import Dict, Any

from src.shared.events.event_bus import EventBus
from src.media_management.domain.media import MediaType
from src.shared.events.domain_events import MediaUploaded, AudioExtracted, MediaDeleted
from src.transcription.tasks.tasks import process_transcription_task
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository
from src.media_management.application.queries.media_queries import MediaQueries # Import MediaQueries

logger = logging.getLogger(__name__)

DEFAULT_TRANSCRIPTION_PROVIDER = "whisper"

async def register_event_handlers(
    event_bus: EventBus, 
    transcription_repository: TranscriptionRepository, 
    media_queries: MediaQueries # Add dependency
) -> None:
    """Registers all transcription-related event handlers."""

    async def handle_media_uploaded(event_data: Dict[str, Any]) -> None:
        """Handles MediaUploaded events for audio files, triggering transcription directly."""
        try:
            if event_data.get("media_type") == MediaType.AUDIO.value:
                media_id = event_data["media_id"]
                media = await media_queries.get_by_id(media_id)
                if not media:
                    logger.error(f"Media {media_id} not found for transcription.")
                    return

                provider = media.transcription_provider or DEFAULT_TRANSCRIPTION_PROVIDER
                logger.info(f"Audio media uploaded. Dispatching transcription task for media {media_id} with provider {provider}")
                
                process_transcription_task.delay(
                    media_id=media_id, 
                    file_path=media.original_file_path,
                    storage_provider=media.storage_provider,
                    transcription_provider=provider
                )
        except Exception as e:
            logger.error(f"Failed to handle MediaUploaded event for transcription: {e}", exc_info=True)

    async def handle_audio_extracted(event_data: Dict[str, Any]) -> None:
        """Handles AudioExtracted events, triggering transcription."""
        try:
            media_id = event_data["media_id"]
            media = await media_queries.get_by_id(media_id)
            if not media:
                logger.error(f"Media {media_id} not found for transcription.")
                return

            provider = media.transcription_provider or DEFAULT_TRANSCRIPTION_PROVIDER
            logger.info(f"Audio extracted. Dispatching transcription task for media {media_id} with provider {provider}")
            
            process_transcription_task.delay(
                media_id=media_id, 
                file_path=event_data["audio_file_path"],
                storage_provider=event_data["storage_provider"],
                transcription_provider=provider
            )
        except Exception as e:
            logger.error(f"Failed to handle AudioExtracted event: {e}", exc_info=True)

    async def handle_media_deleted(event_data: Dict[str, Any]) -> None:
        try:
            media_id = event_data["media_id"]
            logger.info(f"Media deleted event received for media {media_id}. Deleting associated transcription.")
            await transcription_repository.delete_by_media_id(media_id)
        except Exception as e:
            logger.error(f"Failed to handle MediaDeleted event for transcription: {e}", exc_info=True)

    try:
        event_bus.subscribe(MediaUploaded, handle_media_uploaded)
        event_bus.subscribe(AudioExtracted, handle_audio_extracted)
        event_bus.subscribe(MediaDeleted, handle_media_deleted)
        logger.info("Successfully registered transcription event handlers.")
    except Exception as e:
        logger.error(f"Failed to register transcription event handlers: {e}", exc_info=True)
        raise
