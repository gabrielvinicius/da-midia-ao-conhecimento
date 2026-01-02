"""Domain event handlers for text analysis."""

from __future__ import annotations

from typing import Awaitable, Callable
from uuid import UUID

from src.shared.domain.events import TextContentReady

from .dtos import AnalyzeTextCommand
from .ports import TranscriptionQueryPort


def build_text_content_ready_handler(
    service,
    transcription_queries: TranscriptionQueryPort | None = None,
) -> Callable[[TextContentReady], Awaitable[None]]:
    async def handler(event: TextContentReady) -> None:
        if not event.text:
            return

        metadata = event.metadata or {}

        media_id = UUID(event.media_id) if event.media_id else None
        transcription_id = (
            UUID(event.transcription_id) if event.transcription_id else None
        )
        user_id = UUID(event.user_id) if getattr(event, "user_id", None) else None

        # We can run one analysis task that does everything, or split them.
        # The Service orchestrates everything now.

        command = AnalyzeTextCommand(
            media_id=media_id,
            document_id=transcription_id or media_id,  # fallback
            text_content=event.text,
            transcription_id=transcription_id,
            language=metadata.get("language"),
            user_id=user_id,
        )

        await service.analyze_text_content(command)

    return handler


__all__ = ["build_text_content_ready_handler"]
