# src/summarization/application/event_handlers.py
import logging
from typing import Any

from src.shared.events.domain_events import MediaDeleted, TextContentReady


logger = logging.getLogger(__name__)

DEFAULT_SUMMARY_PROVIDER = "huggingface"


async def register_event_handlers(
    event_bus: Any,
    summary_repository: Any,
    media_queries: Any,
    task_scheduler: Any,
) -> None:
    """Registers event handlers that orchestrate summarization workflows."""

    async def handle_text_content_ready(event: TextContentReady) -> None:
        try:
            media_id = event.media_id
            media = await media_queries.get_by_id(media_id)
            if not media:
                logger.error("Media %s not found for summarization", media_id)
                return

            provider = getattr(media, "summarization_provider", None) or event.provider or DEFAULT_SUMMARY_PROVIDER
            logger.info(
                "Dispatching summarization task",
                extra={"media_id": media_id, "provider": provider},
            )

            await task_scheduler.schedule_summarization_task(
                media_id=media_id,
                text_content=event.text_content,
                provider=provider,
            )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to handle TextContentReady event: %s", exc, exc_info=True)

    async def handle_media_deleted(event: MediaDeleted) -> None:
        try:
            await summary_repository.delete_by_media_id(event.media_id)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Failed to handle MediaDeleted event for summaries: %s", exc, exc_info=True)

    event_bus.subscribe(TextContentReady, handle_text_content_ready)
    event_bus.subscribe(MediaDeleted, handle_media_deleted)

