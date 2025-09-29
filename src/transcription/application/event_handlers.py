# src/transcription/application/event_handlers.py
import logging
from typing import Dict, Any

from src.shared.events.event_bus import EventBus
from src.media_management.domain.media import MediaType
from src.shared.events.domain_events import MediaUploaded, AudioExtracted
from src.transcription.tasks.tasks import process_transcription_task

logger = logging.getLogger(__name__)


async def register_event_handlers(event_bus: EventBus) -> None:
    """Registers all transcription-related event handlers."""

    async def handle_media_uploaded(event_data: Dict[str, Any]) -> None:
        """Handles MediaUploaded events for audio files, triggering transcription directly."""
        try:
            if event_data.get("media_type") == MediaType.AUDIO.value:
                media_id = event_data["media_id"]
                file_path = event_data["file_path"]
                storage_provider = event_data["storage_provider"]
                logger.info(f"Audio media uploaded. Dispatching transcription task for media {media_id}")
                # For direct audio uploads, we can use a default transcription provider.
                process_transcription_task.delay(
                    media_id=media_id, 
                    file_path=file_path, 
                    storage_provider=storage_provider,
                    transcription_provider="whisper" # Default provider
                )
        except KeyError as e:
            logger.error(f"Missing required field in MediaUploaded event: {e}")
        except Exception as e:
            logger.error(f"Failed to handle MediaUploaded event for transcription: {e}", exc_info=True)

    async def handle_audio_extracted(event_data: Dict[str, Any]) -> None:
        """Handles AudioExtracted events, triggering transcription."""
        try:
            media_id = event_data["media_id"]
            audio_file_path = event_data["audio_file_path"]
            storage_provider = event_data["storage_provider"]
            logger.info(f"Audio extracted. Dispatching transcription task for media {media_id}")
            process_transcription_task.delay(
                media_id=media_id, 
                file_path=audio_file_path, 
                storage_provider=storage_provider,
                transcription_provider="whisper" # Default provider
            )
        except KeyError as e:
            logger.error(f"Missing required field in AudioExtracted event: {e}")
        except Exception as e:
            logger.error(f"Failed to handle AudioExtracted event: {e}", exc_info=True)

    try:
        event_bus.subscribe(MediaUploaded, handle_media_uploaded)
        event_bus.subscribe(AudioExtracted, handle_audio_extracted)
        logger.info("Successfully registered transcription event handlers for MediaUploaded and AudioExtracted.")
    except Exception as e:
        logger.error(f"Failed to register transcription event handlers: {e}", exc_info=True)
        raise
