"""Domain event handlers for text analysis."""

from __future__ import annotations

from typing import Awaitable, Callable

from src.shared.events.domain_events import TextContentReady


def build_text_content_ready_handler(service) -> Callable[[TextContentReady], Awaitable[None]]:
    async def handler(event: TextContentReady) -> None:
        if not event.text_content:
            return

        metadata = event.metadata or {}

        # schedule summarization
        await service.schedule_summarization_task(
            transcription_id=event.transcription_id,
            media_id=event.media_id,
            text_content=event.text_content,
            provider=metadata.get("summarization_provider"),
            options=metadata.get("summarization_options", {}),
        )

        # schedule sentiment
        await service.schedule_sentiment_analysis_task(
            transcription_id=event.transcription_id,
            text=event.text_content,
            provider=metadata.get("sentiment_provider"),
            model=metadata.get("sentiment_model"),
            media_id=event.media_id,
            language=metadata.get("language"),
        )

        # schedule topic modeling
        await service.schedule_topic_modeling_task(
            media_id=event.media_id,
            text_content=event.text_content,
            provider=metadata.get("topic_provider"),
            language=metadata.get("language"),
            options=metadata.get("topic_options", {}),
        )

    return handler


__all__ = ["build_text_content_ready_handler"]

