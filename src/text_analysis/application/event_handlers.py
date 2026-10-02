"""Domain event handlers for text analysis."""

from __future__ import annotations

from typing import Awaitable, Callable

from src.shared.domain.events import TextContentReady

from src.shared.domain.value_objects.identifiers import parse_id, parse_media_id

from .dtos import AnalyzeTextCommand
from .ports import TranscriptionQueryPort


def build_text_content_ready_handler(
    service,
    transcription_queries: TranscriptionQueryPort | None = None,
) -> Callable[[TextContentReady], Awaitable[None]]:
    async def handler(event: TextContentReady) -> None:
        if not event.text:
            return

        media_id = parse_media_id(event.media_id)
        transcription_id = parse_id(event.transcription_id)
        user_id = parse_id(event.user_id)

        command = AnalyzeTextCommand(
            media_id=media_id,
            document_id=transcription_id or media_id,  # fallback
            text_content=event.text,
            transcription_id=transcription_id,
            language=event.language,
            user_id=user_id,
        )

        await service.analyze_text_content(command)

    return handler


__all__ = ["build_text_content_ready_handler"]
