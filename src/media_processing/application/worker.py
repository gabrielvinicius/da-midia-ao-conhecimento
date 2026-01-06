from __future__ import annotations

from typing import Any, Dict
from uuid import UUID

import structlog

from src.media_management.infrastructure.dependencies.builders import (
    build_media_event_handlers,
)
from src.notifications.bootstrap import bootstrap_pipeline_notification_service
from src.shared.domain.events import (
    MediaProcessingFailed,
    MediaProcessingStarted,
    TextContentReady,
    TranscriptionCompleted,
    TranscriptionFailed,
)
from src.shared.infrastructure.database.db import AsyncSessionLocal
from src.shared.infrastructure.messaging.event_bus_factory import get_event_bus
from src.storage.infrastructure.dependencies import StorageServiceFactory

logger = structlog.get_logger(__name__)


class MediaWorkerApp:
    """Encapsulates the worker application logic and event subscriptions.
    
    This class replaces the ad-hoc `_bind_worker_subscribers` function in tasks.py,
    providing a clean, testable entry point for the worker's reactive logic.
    """

    def __init__(self, event_bus=None):
        self.event_bus = event_bus or get_event_bus()
        self._subscribers_bound = False

    def ensure_subscribers(self):
        """Idempotently registers event subscribers for the worker process."""
        if self._subscribers_bound:
            return
        
        self.event_bus.subscribe(TranscriptionCompleted, self._on_transcription_completed)
        self.event_bus.subscribe(TranscriptionFailed, self._on_transcription_failed)
        self.event_bus.subscribe(TextContentReady, self._on_text_content_ready)
        self.event_bus.subscribe(MediaProcessingStarted, self._on_media_processing_started)
        self.event_bus.subscribe(MediaProcessingFailed, self._on_media_processing_failed)
        
        self._subscribers_bound = True
        logger.info("media_processing.worker.subscribers_bound")

    async def _on_transcription_completed(self, event: TranscriptionCompleted) -> None:
        async with AsyncSessionLocal() as session:
            handlers = self._build_media_handlers(session)
            await handlers.handle_transcription_completed(event)

            if getattr(event, "user_id", None):
                service = bootstrap_pipeline_notification_service(session)
                await service.notify(
                    user_id=UUID(str(event.user_id)),
                    message="Transcrição concluída com sucesso.",
                    correlation_id=getattr(event, "correlation_id", None),
                    variables={
                        "media_id": str(event.media_id),
                        "transcription_id": str(event.transcription_id),
                        "evento": "TranscriptionCompleted",
                    },
                )

    async def _on_transcription_failed(self, event: TranscriptionFailed) -> None:
        async with AsyncSessionLocal() as session:
            handlers = self._build_media_handlers(session)
            await handlers.handle_transcription_failed(event)

            if getattr(event, "user_id", None):
                service = bootstrap_pipeline_notification_service(session)
                await service.notify(
                    user_id=UUID(str(event.user_id)),
                    message="Falha ao processar a transcrição.",
                    correlation_id=getattr(event, "correlation_id", None),
                    variables={
                        "media_id": str(event.media_id),
                        "transcription_id": (
                            str(event.transcription_id)
                            if getattr(event, "transcription_id", None)
                            else None
                        ),
                        "erro": getattr(event, "error_message", None),
                        "evento": "TranscriptionFailed",
                    },
                )

    async def _on_text_content_ready(self, event: TextContentReady) -> None:
        if not getattr(event, "text", None):
            return

        async with AsyncSessionLocal() as session:
            handlers = self._build_media_handlers(session)
            await handlers.handle_text_content_ready(event)

        # Trigger Text Analysis Task
        payload: Dict[str, Any] = {
            "media_id": str(event.media_id),
            "transcription_id": (
                str(event.transcription_id)
                if getattr(event, "transcription_id", None)
                else None
            ),
            "user_id": getattr(event, "user_id", None),
            "filename": getattr(event, "filename", None),
            "text_content": getattr(event, "text", None),
            "language": (
                (event.metadata or {}).get("language")
                if isinstance(getattr(event, "metadata", None), dict)
                else None
            ),
            "correlation_id": getattr(event, "correlation_id", None),
        }

        try:
            from src.text_analysis.tasks import analyze_task  # noqa: WPS433

            if hasattr(analyze_task, "delay"):
                analyze_task.delay(**payload)
            else:  # pragma: no cover
                analyze_task(**payload)
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "text_analysis.enqueue_failed",
                media_id=str(event.media_id),
                error=str(exc),
            )

    async def _on_media_processing_started(self, event: MediaProcessingStarted) -> None:
        async with AsyncSessionLocal() as session:
            handlers = self._build_media_handlers(session)
            await handlers.handle_media_processing_started(event)

    async def _on_media_processing_failed(self, event: MediaProcessingFailed) -> None:
        async with AsyncSessionLocal() as session:
            handlers = self._build_media_handlers(session)
            await handlers.handle_media_processing_failed(event)

            user_id = None
            if isinstance(getattr(event, "metadata", None), dict):
                user_id = event.metadata.get("user_id")
            if user_id:
                service = bootstrap_pipeline_notification_service(session)
                await service.notify(
                    user_id=UUID(str(user_id)),
                    message="Falha durante o processamento do arquivo.",
                    correlation_id=getattr(event, "correlation_id", None),
                    variables={
                        "media_id": str(event.media_id),
                        "stage": getattr(event, "stage", None),
                        "erro": getattr(event, "error_message", None),
                        "evento": "MediaProcessingFailed",
                    },
                )

    def _build_media_handlers(self, session):
        return build_media_event_handlers(
            session=session,
            storage_factory=StorageServiceFactory(),
            event_bus=self.event_bus,
        )
