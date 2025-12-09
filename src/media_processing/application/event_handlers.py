"""Event handlers for the media_processing module."""
from __future__ import annotations

import time
from typing import Any, Dict, Optional
from uuid import UUID

import structlog

from src.media_processing.application.services.media_processing_service import MediaProcessingService
from src.providers.domain.interfaces import IProviderRegistry, ProviderType
from src.shared.domain.events import MediaUploaded, TextContentReady
from src.shared.domain.enums import MediaType as _MediaType


logger = structlog.get_logger(__name__).bind(component="media_processing.event_handlers")


class MediaProcessingEventHandlers:
    """Handles domain events related to media processing."""

    def __init__(
        self,
        media_processing_service: MediaProcessingService,
        provider_registry: IProviderRegistry | None = None,
    ) -> None:
        self._media_processing_service = media_processing_service
        self._provider_registry = provider_registry
        self._logger = structlog.get_logger(__name__).bind(component="media_processing.event_handlers")

    async def handle_media_uploaded(
        self,
        event: MediaUploaded,
        *,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Trigger downstream processing whenever a media upload completes."""
        context = context or {}
        try:
            media_id = UUID(event.media_id)
            media_type_value = event.media_type or context.get("media_type")
            media_type = self._resolve_media_type(media_type_value)

            if media_type == _MediaType.TEXT:
                await self._delegate_text_extraction(event, context, media_id)
            else:
                await self._delegate_transcription(event, context, media_id)

            if media_type == _MediaType.VIDEO:
                await self._delegate_video_processing(event, context, media_id)
            else:
                self._logger.debug(
                    "media_uploaded.video_task_skipped",
                    media_id=str(media_id),
                    reason="non_video_media",
                    media_type=str(media_type),
                )

        except Exception as exc:  # pragma: no cover - defensive catch
            self._logger.error(
                "media_uploaded.handler_failed",
                media_id=getattr(event, "media_id", None),
                error=str(exc),
                correlation_id=getattr(event, "correlation_id", None),
            )
            return

    async def _delegate_text_extraction(self, event, context, media_id):
        storage_provider = event.storage_provider or context.get("storage_provider") or "local"
        file_path = getattr(event, "file_path", None) or context.get("file_path")
        
        try:
            from src.media_processing.application.commands.dto import RequestTextExtractionCommand
            command = RequestTextExtractionCommand(
                media_id=media_id,
                file_path=file_path,
                storage_provider=storage_provider,
            )
            await self._media_processing_service.request_text_extraction(command)
            self._logger.debug(
                "media_uploaded.text_extraction_delegated",
                media_id=str(media_id),
            )
        except Exception as exc:
            self._logger.error(
                "media_uploaded.text_extraction_delegation_failed",
                media_id=str(media_id),
                error=str(exc),
            )

    async def _delegate_transcription(self, event, context, media_id):
        storage_provider = event.storage_provider or context.get("storage_provider") or "local"
        # Validate providers
        transcription_provider = self._validate_provider(
            event.transcription_provider
            or context.get("transcription_provider")
            or context.get("provider")
            or "fastwhisper",
            ProviderType.TRANSCRIPTION,
        )
        summarization_provider = self._validate_provider(
            event.summarization_provider or context.get("summarization_provider"),
            ProviderType.SUMMARIZATION,
        )
        sentiment_provider = self._validate_provider(
            event.sentiment_provider or context.get("sentiment_provider"),
            ProviderType.SENTIMENT_ANALYSIS,
        )
        topic_provider = self._validate_provider(
            event.topic_modeling_provider or context.get("topic_modeling_provider"),
            ProviderType.TOPIC_MODELING,
        )
        
        file_path = getattr(event, "file_path", None) or context.get("file_path")
        if not file_path and hasattr(event, "filename"):
             pass

        try:
            from src.media_processing.application.commands.dto import RequestTranscriptionCommand
            command = RequestTranscriptionCommand(
                media_id=media_id,
                file_path=file_path, 
                storage_provider=storage_provider,
                transcription_provider=transcription_provider,
                language=event.language or context.get("language") or "auto",
                file_size_bytes=event.file_size_bytes or context.get("file_size_bytes") or 0,
                summarization_provider=summarization_provider,
                sentiment_provider=sentiment_provider,
                topic_modeling_provider=topic_provider,
            )
            await self._media_processing_service.request_transcription(command)
            self._logger.debug(
                "media_uploaded.transcription_delegated",
                media_id=str(media_id),
            )
        except Exception as exc:
            self._logger.error(
                "media_uploaded.transcription_delegation_failed",
                media_id=str(media_id),
                error=str(exc),
            )

    async def _delegate_video_processing(self, event, context, media_id):
        storage_provider = event.storage_provider or context.get("storage_provider") or "local"
        file_path = getattr(event, "file_path", None) or context.get("file_path")
        
        try:
            from src.media_processing.application.commands.dto import RequestVideoProcessingCommand
            command = RequestVideoProcessingCommand(
                media_id=media_id,
                file_path=file_path,
                storage_provider=storage_provider,
            )
            await self._media_processing_service.request_video_processing(command)
            self._logger.debug(
                "media_uploaded.video_processing_delegation_failed",
                media_id=str(media_id),
            )
        except Exception as exc:
            self._logger.error(
                "media_uploaded.video_processing_delegation_failed",
                media_id=str(media_id),
                error=str(exc),
            )

    def _resolve_media_type(self, media_type_value):
        try:
            from src.shared.domain.enums import MediaType as _MediaType
            if isinstance(media_type_value, _MediaType):
                return media_type_value
            elif media_type_value is not None:
                candidate = str(media_type_value).upper()
                return _MediaType(candidate)
        except Exception:
            pass
        return None

    async def handle_text_content_ready(
        self,
        event: TextContentReady,
        *,
        context: Optional[dict[str, Any]] = None,
    ) -> None:
        """Trigger downstream text analysis once transcription finishes."""
        context = context or {}

        text = (event.text_content or "").strip()
        if not text:
            self._logger.info(
                "text_content_ready.skipped",
                media_id=event.media_id,
                reason="empty_text",
            )
            return

        # Dynamic dispatch to Text Analysis tasks
        try:
            from src.text_analysis.tasks import (
                summarize_task,
                sentiment_task,
                topic_modeling_task,
            )
        except Exception as exc:
            self._logger.warning(
                "text_content_ready.analysis_task_unavailable",
                media_id=event.media_id,
                error=str(exc),
            )
            return

        metadata = event.metadata or {}
        base_payload: Dict[str, Any] = {
            "text": text,
            "media_id": event.media_id,
            "transcription_id": event.transcription_id,
            "language": metadata.get("language") or context.get("language"),
        }

        jobs = [
            (
                summarize_task,
                {
                    **base_payload,
                    "provider": metadata.get("summarization_provider"),
                },
                "summarization",
            ),
            (
                sentiment_task,
                {
                    **base_payload,
                    "provider": metadata.get("sentiment_provider"),
                },
                "sentiment",
            ),
            (
                topic_modeling_task,
                {
                    **base_payload,
                    "provider": metadata.get("topic_provider"),
                },
                "topic_modeling",
            ),
        ]

        for task_fn, payload, name in jobs:
            try:
                if hasattr(task_fn, "delay"):
                    task_fn.delay(payload)
                else:
                    task_fn(payload)
                self._logger.info(
                    "text_content_ready.analysis_enqueued",
                    media_id=event.media_id,
                    transcription_id=event.transcription_id,
                    task=name,
                )
            except Exception as exc:
                self._logger.error(
                    "text_content_ready.analysis_failed",
                    media_id=event.media_id,
                    transcription_id=event.transcription_id,
                    task=name,
                    error=str(exc),
                )

    def _validate_provider(self, name: str | None, provider_type: ProviderType) -> str | None:
        if not name or self._provider_registry is None:
            return name
        active = {
            getattr(p, "name", None) or getattr(p, "get_name", lambda: None)()
            for p in self._provider_registry.get_active_providers(provider_type)
        }
        if name not in active:
            raise ValueError(f"Provider '{name}' not registered/active for {provider_type.value}")
        return name
