# src/sentiment_analysis/application/event_handlers.py
import logging
from typing import Dict, Any

from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import FullTextReadyForAnalysis
from src.sentiment_analysis.tasks.analysis_tasks import analyze_sentiment_task, analyze_topics_task # Import new task

logger = logging.getLogger(__name__)


async def register_event_handlers(event_bus: EventBus) -> None:
    """Registers all analysis-related event handlers."""

    async def handle_full_text_ready(event_data: Dict[str, Any]) -> None:
        """Handles FullTextReadyForAnalysis events by triggering all relevant analysis tasks."""
        try:
            media_id = event_data["media_id"]
            text_content = event_data["text_content"]
            
            logger.info(f"Full text ready for media {media_id}. Dispatching analysis tasks.")
            
            # Trigger sentiment analysis
            analyze_sentiment_task.delay(
                media_id=media_id,
                text_content=text_content
            )
            
            # Trigger topic modeling
            analyze_topics_task.delay(
                media_id=media_id,
                text_content=text_content
            )

        except KeyError as e:
            logger.error(f"Missing required field in FullTextReadyForAnalysis event: {e}")
        except Exception as e:
            logger.error(f"Failed to handle FullTextReadyForAnalysis event: {e}", exc_info=True)

    try:
        event_bus.subscribe(FullTextReadyForAnalysis, handle_full_text_ready)
        logger.info("Successfully registered FullTextReadyForAnalysis handler for all analysis tasks.")
    except Exception as e:
        logger.error(f"Failed to register analysis event handlers: {e}", exc_info=True)
        raise
