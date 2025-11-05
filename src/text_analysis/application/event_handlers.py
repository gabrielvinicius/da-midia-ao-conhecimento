"""Event handlers bridging Text Analysis domain flows."""
from __future__ import annotations

from typing import Any, Callable

import structlog

from src.shared.events.domain_events import TextContentReady

logger = structlog.get_logger(__name__).bind(component="text_analysis.event_handlers")


def build_text_content_ready_handler(
    text_analysis_service: Any,
) -> Callable[[TextContentReady], Any]:
    """Return an async handler that schedules downstream text analysis tasks."""

    async def _handler(event: TextContentReady) -> None:
        if text_analysis_service is None:
            logger.warning(
                "text_content_ready.handler.missing_service",
                media_id=event.media_id,
            )
            return

        text = getattr(event, "text_content", None)
        if not text:
            logger.warning(
                "text_content_ready.handler.no_text",
                media_id=event.media_id,
                transcription_id=event.transcription_id,
            )
            return

        metadata = getattr(event, "metadata", {}) or {}

        summarization_provider = metadata.get("summarization_provider", "builtin")
        summarization_options = metadata.get("summarization_options")

        try:
            await text_analysis_service.schedule_summarization_task(
                media_id=event.media_id,
                text_content=text,
                provider=summarization_provider,
                options=summarization_options,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning(
                "text_content_ready.summarization_failed",
                media_id=event.media_id,
                error=str(exc),
            )

        if event.transcription_id:
            sentiment_provider = metadata.get("sentiment_provider", "builtin")
            sentiment_model = metadata.get("sentiment_model")
            language = metadata.get("language")
            try:
                await text_analysis_service.schedule_sentiment_analysis_task(
                    transcription_id=event.transcription_id,
                    text=text,
                    provider=sentiment_provider,
                    model=sentiment_model,
                    media_id=event.media_id,
                    language=language,
                )
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.warning(
                    "text_content_ready.sentiment_failed",
                    media_id=event.media_id,
                    transcription_id=event.transcription_id,
                    error=str(exc),
                )

        topic_provider = metadata.get("topic_provider")
        if topic_provider is not None:
            topic_language = metadata.get("language", "en")
            topic_options = metadata.get("topic_options")
            try:
                await text_analysis_service.schedule_topic_modeling_task(
                    media_id=event.media_id,
                    text_content=text,
                    provider=topic_provider,
                    language=topic_language,
                    options=topic_options,
                )
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.warning(
                    "text_content_ready.topic_modeling_failed",
                    media_id=event.media_id,
                    error=str(exc),
                )

    return _handler


__all__ = ["build_text_content_ready_handler"]
