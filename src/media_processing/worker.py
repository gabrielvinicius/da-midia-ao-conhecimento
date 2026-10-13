"""Assinaturas de eventos dos workers (camada de montagem)."""
from __future__ import annotations

from typing import Any, Dict, Optional

import structlog

from src.media_processing.application.ports import AnalysisRequestPort
from src.shared.application.event_bus import SupportsEventBus
from src.media_processing.infrastructure.adapters.celery_task_schedulers import (
    CeleryAnalysisRequester,
)
from src.shared.domain.events import (
    MediaProcessingFailed,
    MediaUploaded,
    TextContentReady,
)
from src.shared.infrastructure.database.db import AsyncSessionLocal
from src.storage.infrastructure.dependencies import StorageServiceFactory

logger = structlog.get_logger(__name__)


class MediaWorkerApp:
    """Montagem do processamento no worker: começa a transcrição de uma mídia
    anunciada e pede a análise quando o texto fica pronto.

    O estado da mídia e os avisos não ficam aqui: os módulos de mídias e de
    avisos assinam os mesmos eventos (media_management/worker.py e
    notifications/worker.py).
    """

    def __init__(
        self,
        event_bus: SupportsEventBus,
        analysis_requester: Optional[AnalysisRequestPort] = None,
    ):
        # O barramento do processo, em que as tarefas publicam. Antes, sem ele
        # era criado um barramento novo, em que ninguém publicava.
        self.event_bus = event_bus
        # O pedido de análise segue pelo nome da tarefa, sem importar text_analysis.
        self.analysis_requester: AnalysisRequestPort = analysis_requester or CeleryAnalysisRequester()

    def subscribe(self) -> None:
        # Mídia anunciada no worker (recuperação de envios que não começaram).
        self.event_bus.subscribe(MediaUploaded, self._on_media_uploaded)
        self.event_bus.subscribe(TextContentReady, self._on_text_content_ready)

    async def _on_media_uploaded(self, event: MediaUploaded) -> None:
        from src.media_processing.infrastructure.dependencies.builders import (
            build_media_processing_event_handlers,
        )

        async with AsyncSessionLocal() as session:
            handlers = build_media_processing_event_handlers(
                session=session,
                storage_factory=StorageServiceFactory(),
                event_bus=self.event_bus,
                storage_provider=event.storage_provider or "local",
            )
            await handlers.handle_media_uploaded(event)

    async def _on_text_content_ready(self, event: TextContentReady) -> None:
        if not event.text:  # a transcrição e a extração já falham sem texto
            logger.warning("text_analysis.empty_text_ignored", media_id=str(event.media_id))
            return

        # A mídia já passou a "em análise" ao receber TranscriptionCompleted.
        payload: Dict[str, Any] = {
            "media_id": str(event.media_id),
            "transcription_id": str(event.transcription_id) if event.transcription_id else None,
            "user_id": event.user_id,
            "filename": event.filename,
            "language": event.language,
            "correlation_id": event.correlation_id,
        }

        try:
            self.analysis_requester.request_analysis(payload)
        except Exception as exc:
            # Antes, só um aviso no log: a mídia ficava sem análise e nada a
            # recuperava. Agora ela falha de forma visível e pode ser
            # reprocessada pelo usuário.
            logger.error("text_analysis.enqueue_failed", media_id=str(event.media_id), error=str(exc))
            await self.event_bus.publish(
                MediaProcessingFailed(
                    media_id=str(event.media_id),
                    stage="text_analysis",
                    error_message="Não foi possível agendar a análise do texto. Tente reprocessar a mídia.",
                    user_id=payload["user_id"],
                    correlation_id=payload["correlation_id"],
                )
            )


def bind_processing_subscribers(event_bus: SupportsEventBus) -> None:
    MediaWorkerApp(event_bus=event_bus).subscribe()


__all__ = ["MediaWorkerApp", "bind_processing_subscribers"]
