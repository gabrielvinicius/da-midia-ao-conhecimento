# src/summarization/application/event_handlers.py
import logging
from typing import Dict, Any

from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import TextContentReady, MediaDeleted # Import MediaDeleted
from src.summarization.tasks.summary_tasks import process_summary_task
from src.summarization.infrastructure.summary_repository import SummaryRepository # Import repository

logger = logging.getLogger(__name__)


async def register_event_handlers(event_bus: EventBus, summary_repository: SummaryRepository):
    """Registers all summarization-related event handlers."""

    async def handle_text_content_ready(event_data: Dict[str, Any]):
        """Handles TextContentReady events by triggering the summarization task."""
        try:
            media_id = event_data["media_id"]
            text_content = event_data["text_content"]
            logger.info(f"Text content ready for media {media_id}. Dispatching summarization task.")
            process_summary_task.delay(
                media_id=media_id, 
                text_content=text_content,
                provider="huggingface"
            )
        except KeyError as e:
            logger.error(f"Missing required field in TextContentReady event: {e}")
        except Exception as e:
            logger.error(f"Failed to handle TextContentReady event: {e}", exc_info=True)

    async def handle_media_deleted(event_data: Dict[str, Any]) -> None:
        """Handles MediaDeleted events by deleting associated summary."""
        try:
            media_id = event_data["media_id"]
            logger.info(f"Media deleted event received for media {media_id}. Deleting associated summary.")
            success = await summary_repository.delete_by_media_id(media_id)
            if success:
                logger.info(f"Summary for media {media_id} deleted successfully.")
            else:
                logger.warning(f"No summary found or deleted for media {media_id}.")
        except KeyError as e:
            logger.error(f"Missing required field in MediaDeleted event: {e}")
        except Exception as e:
            logger.error(f"Failed to handle MediaDeleted event for summary: {e}", exc_info=True)

    try:
        event_bus.subscribe(TextContentReady, handle_text_content_ready)
        event_bus.subscribe(MediaDeleted, handle_media_deleted) # Subscribe to new event
        logger.info("Successfully registered summarization event handlers.")
    except Exception as e:
        logger.error(f"Failed to register summarization event handlers: {e}", exc_info=True)
        raise
