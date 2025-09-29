# src/summarization/application/event_handlers.py
import logging
from typing import Dict, Any

from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import TextContentReady
from src.summarization.tasks.summary_tasks import process_summary_task

logger = logging.getLogger(__name__)


async def register_event_handlers(event_bus: EventBus):
    """Registers all summarization-related event handlers."""

    async def handle_text_content_ready(event_data: Dict[str, Any]):
        """Handles TextContentReady events by triggering the summarization task."""
        try:
            media_id = event_data["media_id"]
            text_content = event_data["text_content"]
            logger.info(f"Text content ready for media {media_id}. Dispatching summarization task.")

            # For now, we use a default provider. This could be made configurable.
            process_summary_task.delay(
                media_id=media_id, 
                text_content=text_content,
                provider="huggingface"
            )

        except KeyError as e:
            logger.error(f"Missing required field in TextContentReady event: {e}")
        except Exception as e:
            logger.error(f"Failed to handle TextContentReady event: {e}", exc_info=True)

    try:
        event_bus.subscribe(TextContentReady, handle_text_content_ready)
        logger.info("Successfully registered TextContentReady handler for summarization.")
    except Exception as e:
        logger.error(f"Failed to register summarization event handlers: {e}", exc_info=True)
        raise
