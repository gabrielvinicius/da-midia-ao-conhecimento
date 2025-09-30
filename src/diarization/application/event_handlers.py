# src/diarization/application/event_handlers.py
import logging
from typing import Dict, Any

from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import TranscriptionWithTimestampsReady
from src.diarization.tasks.diarization_tasks import diarize_audio_task

logger = logging.getLogger(__name__)


async def register_event_handlers(event_bus: EventBus) -> None:
    """Registers all diarization-related event handlers."""

    async def handle_transcription_ready(event_data: Dict[str, Any]) -> None:
        """Handles TranscriptionWithTimestampsReady events by triggering the diarization task."""
        try:
            media_id = event_data["media_id"]
            audio_file_path = event_data["audio_file_path"]
            storage_provider = event_data["storage_provider"]
            
            logger.info(f"Transcription ready for media {media_id}. Dispatching diarization task.")
            
            diarize_audio_task.delay(
                media_id=media_id,
                audio_file_path=audio_file_path,
                storage_provider=storage_provider
            )

        except KeyError as e:
            logger.error(f"Missing required field in TranscriptionWithTimestampsReady event: {e}")
        except Exception as e:
            logger.error(f"Failed to handle TranscriptionWithTimestampsReady event for diarization: {e}", exc_info=True)

    try:
        event_bus.subscribe(TranscriptionWithTimestampsReady, handle_transcription_ready)
        logger.info("Successfully registered TranscriptionWithTimestampsReady handler for diarization.")
    except Exception as e:
        logger.error(f"Failed to register diarization event handlers: {e}", exc_info=True)
        raise
