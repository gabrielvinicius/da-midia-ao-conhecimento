"""Backward-compatible handler for text processing command flow."""

from __future__ import annotations

from typing import Any, Callable

import fitz  # type: ignore[import-untyped]

from src.media_management.domain.media import MediaStatus
from src.shared.events.domain_events import TextContentReady

from .commands import ProcessTextCommand


class ProcessTextCommandHandler:
    """Legacy handler that extracts text content and publishes domain events."""

    def __init__(
        self,
        *,
        media_queries: Any,
        media_repository: Any,
        storage_service_factory: Callable[[str], Any],
        event_bus: Any,
    ) -> None:
        self._media_queries = media_queries
        self._media_repository = media_repository
        self._storage_service_factory = storage_service_factory
        self._event_bus = event_bus

    async def handle(self, command: ProcessTextCommand) -> None:
        media = await self._media_queries.get_by_id(command.media_id)
        if media is None:
            raise ValueError("Media not found")

        storage_service = self._storage_service_factory(command.storage_provider)
        payload = await storage_service.download(command.file_path)
        if isinstance(payload, (list, tuple)):
            file_bytes = payload[0]
            filename = payload[1] if len(payload) > 1 else command.file_path
        else:
            file_bytes = payload
            filename = command.file_path

        media_in_progress = media.with_status(MediaStatus.PROCESSING)
        await self._media_repository.save(media_in_progress)

        text_content = self._extract_text(file_bytes, filename)

        media_completed = media_in_progress.with_status(MediaStatus.COMPLETED)
        await self._media_repository.save(media_completed)

        await self._event_bus.publish(
            TextContentReady(
                media_id=str(media_completed.id),
                text_content=text_content,
            )
        )

    def _extract_text(self, file_bytes: bytes, filename: str) -> str:
        if filename.lower().endswith((".pdf",)):
            with fitz.open(stream=file_bytes, filetype="pdf") as doc:  # type: ignore[call-arg]
                return "\n".join(page.get_text() for page in doc)
        return file_bytes.decode("utf-8", errors="ignore")


__all__ = ["ProcessTextCommandHandler"]
