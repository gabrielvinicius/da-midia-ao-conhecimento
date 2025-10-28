"""Event registrations for the sentiment analysis module."""

import logging
from typing import Any, Dict

from src.shared.application.task_orchestrator import schedule_sentiment_analysis
from src.shared.events.domain_events import TextContentReady
from src.shared.events.event_bus import EventBus

logger = logging.getLogger(__name__)


async def register_event_handlers(event_bus: EventBus) -> None:
    """Register domain event handlers related to sentiment analysis."""

    async def handle_text_content_ready(event_data: Dict[str, Any]) -> None:
        try:
            media_id = event_data["media_id"]
            text_content = event_data["text_content"]
            provider = event_data.get("provider", "huggingface")

            logger.info(
                "sentiment_analysis.event.received",
                media_id=media_id,
                provider=provider,
            )
            schedule_sentiment_analysis(
                media_id=media_id,
                text_content=text_content,
                provider=provider,
            )
        except KeyError as exc:
            logger.error(
                "sentiment_analysis.event.invalid_payload",
                missing=str(exc),
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(
                "sentiment_analysis.event.handler_failed",
                error=str(exc),
                exc_info=True,
            )

    try:
        event_bus.subscribe(TextContentReady, handle_text_content_ready)
        logger.info("sentiment_analysis.event.handlers_registered")
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(
            "sentiment_analysis.event.registration_failed",
            error=str(exc),
            exc_info=True,
        )
        raise


__all__ = ["register_event_handlers"]

