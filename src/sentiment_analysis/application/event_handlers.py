# src/sentiment_analysis/application/event_handlers.py
import logging
from typing import Dict, Any

from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import TextContentReady
# FIXED: Application should not import Tasks directly (Infrastructure concern)
from src.shared.application.task_orchestrator import schedule_sentiment_analysis

logger = logging.getLogger(__name__)


async def register_event_handlers(event_bus: EventBus) -> None:
    """Registers all sentiment analysis-related event handlers."""

    async def handle_text_content_ready(event_data: Dict[str, Any]) -> None:
        """Handles TextContentReady events by triggering the sentiment analysis task."""
        try:
            media_id = event_data["media_id"]
            text_content = event_data["text_content"]
            logger.info(f"Text content ready for media {media_id}. Dispatching sentiment analysis task.")

            # For now, we use a default provider. This could be made configurable.
            analyze_sentiment_task.delay(
                media_id=media_id, 
                text_content=text_content,
                provider="huggingface"
            )
        except KeyError as e:
            logger.error(f"Missing required field in TextContentReady event for sentiment analysis: {e}")
        except Exception as e:
            logger.error(f"Failed to handle TextContentReady event for sentiment analysis: {e}", exc_info=True)

    try:
        event_bus.subscribe(TextContentReady, handle_text_content_ready)
        logger.info("Successfully registered TextContentReady handler for sentiment analysis.")
    except Exception as e:
        logger.error(f"Failed to register sentiment analysis event handlers: {e}", exc_info=True)
        raise
