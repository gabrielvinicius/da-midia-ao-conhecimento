# src/transcription/application/event_handlers.py
import logging
from typing import Dict, Any

from src.shared.events.event_bus import EventBus
from src.media_management.domain.media import MediaType
from src.shared.events.domain_events import MediaUploaded, AudioExtracted, MediaDeleted, DiarizationCompleted # Import DiarizationCompleted
from src.transcription.tasks.tasks import process_transcription_task, align_diarization_task # Import new task
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository
from src.media_management.application.queries.media_queries import MediaQueries

logger = logging.getLogger(__name__)

DEFAULT_TRANSCRIPTION_PROVIDER = "whisper"

async def register_event_handlers(
    event_bus: EventBus, 
    transcription_repository: TranscriptionRepository, 
    media_queries: MediaQueries
) -> None:
    """Registers all transcription-related event handlers."""

    async def handle_media_uploaded(event_data: Dict[str, Any]) -> None:
        # ... (implementation remains the same)
        pass

    async def handle_audio_extracted(event_data: Dict[str, Any]) -> None:
        # ... (implementation remains the same)
        pass

    async def handle_media_deleted(event_data: Dict[str, Any]) -> None:
        # ... (implementation remains the same)
        pass

    async def handle_diarization_completed(event_data: Dict[str, Any]) -> None:
        """Handles DiarizationCompleted events by triggering the alignment task."""
        try:
            media_id = event_data["media_id"]
            diarization_result = event_data["diarization_result"]
            logger.info(f"Diarization completed for media {media_id}. Dispatching alignment task.")
            align_diarization_task.delay(media_id=media_id, diarization_result=diarization_result)
        except KeyError as e:
            logger.error(f"Missing required field in DiarizationCompleted event: {e}")
        except Exception as e:
            logger.error(f"Failed to handle DiarizationCompleted event for alignment: {e}", exc_info=True)

    try:
        event_bus.subscribe(MediaUploaded, handle_media_uploaded)
        event_bus.subscribe(AudioExtracted, handle_audio_extracted)
        event_bus.subscribe(MediaDeleted, handle_media_deleted)
        event_bus.subscribe(DiarizationCompleted, handle_diarization_completed) # Subscribe to new event
        logger.info("Successfully registered all transcription event handlers.")
    except Exception as e:
        logger.error(f"Failed to register transcription event handlers: {e}", exc_info=True)
        raise

# Keep the original implementations for brevity in this view
    async def handle_media_uploaded(event_data: Dict[str, Any]) -> None:
        try:
            if event_data.get("media_type") == MediaType.AUDIO.value:
                media_id = event_data["media_id"]
                media = await media_queries.get_by_id(media_id)
                if not media: return
                provider = media.transcription_provider or DEFAULT_TRANSCRIPTION_PROVIDER
                process_transcription_task.delay(media_id=media_id, file_path=media.original_file_path, storage_provider=media.storage_provider, transcription_provider=provider)
        except Exception as e:
            logger.error(f"Failed to handle MediaUploaded event for transcription: {e}", exc_info=True)

    async def handle_audio_extracted(event_data: Dict[str, Any]) -> None:
        try:
            media_id = event_data["media_id"]
            media = await media_queries.get_by_id(media_id)
            if not media: return
            provider = media.transcription_provider or DEFAULT_TRANSCRIPTION_PROVIDER
            process_transcription_task.delay(media_id=media_id, file_path=event_data["audio_file_path"], storage_provider=event_data["storage_provider"], transcription_provider=provider)
        except Exception as e:
            logger.error(f"Failed to handle AudioExtracted event: {e}", exc_info=True)

    async def handle_media_deleted(event_data: Dict[str, Any]) -> None:
        try:
            media_id = event_data["media_id"]
            await transcription_repository.delete_by_media_id(media_id)
        except Exception as e:
            logger.error(f"Failed to handle MediaDeleted event for transcription: {e}", exc_info=True)
