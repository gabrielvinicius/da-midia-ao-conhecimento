# src/text_processing/application/event_handlers.py
import logging
from typing import Dict, Any

from src.shared.events.event_bus import EventBus
from src.media_management.domain.media import MediaType
from src.shared.events.domain_events import MediaUploaded
# FIXED: Application should not import Tasks directly (Infrastructure concern)
from src.shared.application.task_orchestrator import schedule_text_processing

logger = logging.getLogger(__name__)


async def register_event_handlers(event_bus: EventBus) -> None:
    """Registers all text processing-related event handlers."""

    async def handle_media_uploaded(event_data: Dict[str, Any]) -> None:
        """Handles MediaUploaded events by triggering the text processing task if the media is a text file."""
        try:
            if event_data.get("media_type") == MediaType.TEXT.value:
                media_id = event_data["media_id"]
                file_path = event_data["file_path"]
                storage_provider = event_data["storage_provider"]
                logger.info(f"Text media uploaded. Dispatching text processing task for media {media_id}")
                process_text_task.delay(
                    media_id=media_id, 
                    file_path=file_path, 
                    storage_provider=storage_provider
                )

        except KeyError as e:
            logger.error(f"Missing required field in MediaUploaded event data: {e}")
        except Exception as e:
            logger.error(f"Failed to handle MediaUploaded event for text processing: {e}", exc_info=True)

    try:
        event_bus.subscribe(MediaUploaded, handle_media_uploaded)
        logger.info("Successfully registered MediaUploaded handler for text processing.")
    except Exception as e:
        logger.error(f"Failed to register text processing event handlers: {e}", exc_info=True)
        raise
