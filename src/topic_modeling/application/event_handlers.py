# src/topic_modeling/application/event_handlers.py
import logging
from typing import Dict, Any

from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import TextContentReady
# FIXED: Application should not import Tasks directly (Infrastructure concern)
from src.shared.application.task_orchestrator import schedule_topic_modeling

logger = logging.getLogger(__name__)


async def register_event_handlers(event_bus: EventBus) -> None:
    """Registers all topic modeling-related event handlers."""

    async def handle_text_content_ready(event_data: Dict[str, Any]) -> None:
        """Handles TextContentReady events by triggering the topic modeling task."""
        try:
            media_id = event_data["media_id"]
            text_content = event_data["text_content"]
            logger.info(f"Text content ready for media {media_id}. Dispatching topic modeling task.")

            # For now, we use a default provider. This could be made configurable.
            schedule_topic_modeling(
                media_id=media_id,
                text_content=text_content,
                provider="sklearn_lda",
                language=event_data.get("language", "en"),
                options=event_data.get("options"),
            )
        except KeyError as e:
            logger.error(f"Missing required field in TextContentReady event for topic modeling: {e}")
        except Exception as e:
            logger.error(f"Failed to handle TextContentReady event for topic modeling: {e}", exc_info=True)

    try:
        event_bus.subscribe(TextContentReady, handle_text_content_ready)
        logger.info("Successfully registered TextContentReady handler for topic modeling.")
    except Exception as e:
        logger.error(f"Failed to register topic modeling event handlers: {e}", exc_info=True)
        raise
