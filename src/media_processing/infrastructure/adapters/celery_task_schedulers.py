"""Agendadores Celery: enviam tarefas pelo nome, sem importar o módulo das tarefas.

O nome de cada tarefa é um contrato compartilhado (src.shared.events.
integration_events). Enviar pelo nome mantém a infraestrutura independente
da camada de montagem (tasks.py) e dos outros módulos.
"""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

import structlog

from src.shared.events.integration_events import (
    QUEUE_TEXT_ANALYSIS,
    QUEUE_TRANSCRIPTION,
    QUEUE_TRANSCRIPTION_FAST,
    TASK_MEDIA_TEXT_EXTRACTION,
    TASK_MEDIA_TRANSCRIPTION,
    TASK_TEXT_ANALYSIS_ANALYZE,
)

logger = structlog.get_logger(__name__)

FAST_LANE_MAX_BYTES = 50 * 1024 * 1024


# Uma queda curta do Redis não deve perder a tarefa: o envio tenta de novo
# por alguns segundos antes de desistir (e o chamador tratar a falha).
SEND_RETRY_POLICY = {"max_retries": 4, "interval_start": 1, "interval_step": 2, "interval_max": 5}


def _send(task_name: str, kwargs: dict, queue: str):
    from src.celery_app import celery

    return celery.send_task(
        task_name, kwargs=kwargs, queue=queue, retry=True, retry_policy=SEND_RETRY_POLICY
    )


class CeleryTextTaskScheduler:
    """Agenda a extração de texto de documentos e imagens."""

    async def schedule_text_extraction(
        self,
        media_id: UUID,
        file_path: str,
        storage_provider: str,
        user_id: str | None = None,
        filename: str | None = None,
        triggered_by: str | None = None,
        actor_id: str | None = None,
        correlation_id: str | None = None,
    ) -> Any:
        queue = QUEUE_TEXT_ANALYSIS
        task = _send(
            TASK_MEDIA_TEXT_EXTRACTION,
            {
                "media_id": str(media_id),
                "file_path": file_path,
                "storage_provider": storage_provider,
                "user_id": user_id,
                "filename": filename,
                "triggered_by": triggered_by,
                "actor_id": actor_id,
                "correlation_id": correlation_id or str(media_id),
            },
            queue,
        )
        logger.info(
            "celery_task_scheduler.text_extraction_scheduled",
            media_id=str(media_id),
            task_id=task.id,
            queue=queue,
        )
        return {"task_id": task.id}


class CeleryTranscriptionTaskScheduler:
    """Agenda a transcrição; arquivos pequenos vão para a fila rápida."""

    async def schedule_transcription(
        self,
        transcription_id: UUID,
        media_id: UUID,
        file_path: str,
        storage_provider: str,
        transcription_provider: str,
        language: str,
        file_size_bytes: int | None = None,
        user_id: Optional[str] = None,
        filename: Optional[str] = None,
        triggered_by: Optional[str] = None,
        actor_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ) -> Any:
        queue = QUEUE_TRANSCRIPTION
        if file_size_bytes and file_size_bytes < FAST_LANE_MAX_BYTES:
            queue = QUEUE_TRANSCRIPTION_FAST

        task = _send(
            TASK_MEDIA_TRANSCRIPTION,
            {
                "media_id": str(media_id),
                "file_path": file_path,
                "storage_provider": storage_provider,
                "transcription_provider": transcription_provider,
                "transcription_id": str(transcription_id),
                "language": language,
                "file_size_bytes": file_size_bytes,
                "correlation_id": correlation_id or str(media_id),
                "user_id": user_id,
                "filename": filename,
                "triggered_by": triggered_by,
                "actor_id": actor_id,
            },
            queue,
        )
        logger.info(
            "celery_task_scheduler.transcription_task_scheduled",
            media_id=str(media_id),
            task_id=task.id,
            queue=queue,
        )
        return {"task_id": task.id}


class CeleryAnalysisRequester:
    """Pede a análise do texto ao módulo text_analysis, pelo nome da tarefa."""

    def request_analysis(self, payload: dict) -> None:
        _send(TASK_TEXT_ANALYSIS_ANALYZE, payload, QUEUE_TEXT_ANALYSIS)


__all__ = [
    "CeleryAnalysisRequester",
    "CeleryTextTaskScheduler",
    "CeleryTranscriptionTaskScheduler",
]
