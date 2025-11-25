"""Lightweight coordinator for dispatching Celery media tasks."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional
from uuid import UUID

import structlog

from src.media_processing.application.dispatch_repository import (
    DispatchRecord,
    MediaDispatchRepository,
)


@dataclass(slots=True)
class DispatchAction:
    """Represents a single task to enqueue for a media item."""

    name: str
    payload: Dict[str, object]
    fatal: bool = False


class MediaDispatchOrchestrator:
    """Encapsulates the logic for selecting processing actions per media."""

    def __init__(self, repository: Optional[MediaDispatchRepository] = None) -> None:
        self._repository = repository or MediaDispatchRepository()
        self._logger = structlog.get_logger(__name__).bind(component="media_processing.dispatch")

    def prepare_actions(self, media_id: UUID) -> List[DispatchAction]:
        """Mark the media as processing and return the actions that should run."""

        context = self._repository.mark_processing(media_id)
        if context is None:
            self._logger.warning("dispatch.media_not_found", media_id=str(media_id))
            return []

        if not context.file_path:
            reason = "missing file path for media"
            self._logger.error("dispatch.missing_file_path", media_id=str(media_id))
            self._repository.mark_failed(media_id, reason)
            return []

        actions = self._build_actions(context)
        if not actions:
            self._logger.info("dispatch.no_actions", media_id=str(media_id))
        return actions

    def mark_failed(self, media_id: UUID, reason: str) -> None:
        self._repository.mark_failed(media_id, reason)

    # ------------------------------------------------------------------
    def _build_actions(self, context: DispatchRecord) -> List[DispatchAction]:
        normalized_type = (context.media_type or "").upper()

        if normalized_type == "TEXT":
            return [
                DispatchAction(
                    name="text_document",
                    payload={
                        "media_id": str(context.media_id),
                        "file_path": context.file_path,
                        "storage_provider": context.storage_provider,
                        "extraction_method": "basic",
                        "language": context.language,
                        "summarization_provider": context.summarization_provider,
                        "sentiment_provider": context.sentiment_provider,
                        "topic_modeling_provider": context.topic_modeling_provider,
                    },
                    fatal=True,
                )
            ]

        actions: List[DispatchAction] = [
            DispatchAction(
                name="transcription",
                payload={
                    "media_id": str(context.media_id),
                    "file_path": context.file_path,
                    "storage_provider": context.storage_provider,
                    "transcription_provider": context.transcription_provider,
                    "language": context.language,
                    "file_size_bytes": context.file_size_bytes,
                    "summarization_provider": context.summarization_provider,
                    "sentiment_provider": context.sentiment_provider,
                    "topic_modeling_provider": context.topic_modeling_provider,
                },
                fatal=True,
            )
        ]

        if normalized_type == "VIDEO":
            actions.append(
                DispatchAction(
                    name="video",
                    payload={
                        "media_id": str(context.media_id),
                        "file_path": context.file_path,
                        "storage_provider": context.storage_provider,
                        "file_size_bytes": context.file_size_bytes,
                    },
                    fatal=False,
                )
            )

        return actions


__all__ = ["DispatchAction", "MediaDispatchOrchestrator"]
