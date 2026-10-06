"""Tarefas Celery do processamento (camada de montagem: liga serviços e adaptadores).

As reações aos eventos são registradas uma vez por processo, em
src/worker_subscriptions.py; aqui ficam só as tarefas.
"""
import asyncio
from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from celery import shared_task

from src.media_processing.config.settings import processing_settings
from src.media_processing.infrastructure.dependencies.builders import (
    build_stalled_processing_monitor,
    build_text_extraction_service,
    build_transcription_runner,
)
from src.shared.events.integration_events import (
    TASK_MEDIA_SWEEP_STALLED,
    TASK_MEDIA_TEXT_EXTRACTION,
    TASK_MEDIA_TRANSCRIPTION,
)
from src.shared.infrastructure.database.db import AsyncSessionLocal
from src.shared.infrastructure.messaging.process_bus import process_event_bus
from src.shared.infrastructure.tasks.retry import (
    PIPELINE_MAX_RETRIES,
    is_final_attempt,
    retry_unless_permanent,
)

logger = structlog.get_logger(__name__)

# Salvaguarda: nenhuma tentativa passa do prazo máximo de processamento. A
# verificação de mídias paradas encerra antes a que passou do prazo calculado
# pela duração; este limite vale mesmo se a verificação não rodar.
PROCESSING_TIME_LIMIT_SECONDS = int(processing_settings.stall_maximum_hours * 3600)


@shared_task(
    bind=True,
    name=TASK_MEDIA_TEXT_EXTRACTION,
    max_retries=PIPELINE_MAX_RETRIES,
    time_limit=PROCESSING_TIME_LIMIT_SECONDS,
)
def process_text_extraction_task(
    self,
    media_id: str,
    file_path: str,
    storage_provider: str,
    user_id: Optional[str] = None,
    filename: Optional[str] = None,
    correlation_id: Optional[str] = None,
    **_older_fields: Any,  # mensagens enfileiradas por versões anteriores
) -> None:
    logger.info("text_extraction.task_started", media_id=media_id)

    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            service = build_text_extraction_service(
                session=session,
                event_bus=process_event_bus(),
                storage_provider=storage_provider,
            )
            await service.execute_text_extraction(
                media_id=UUID(media_id),
                file_path=file_path,
                storage_provider=storage_provider,
                final_attempt=is_final_attempt(self),
                correlation_id=correlation_id,
                user_id=user_id,
                filename=filename,
            )

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.error("text_extraction.task_failed", error=str(exc), media_id=media_id)
        retry_unless_permanent(self, exc)
        raise


@shared_task(
    bind=True,
    name=TASK_MEDIA_TRANSCRIPTION,
    max_retries=PIPELINE_MAX_RETRIES,
    time_limit=PROCESSING_TIME_LIMIT_SECONDS,
)
def process_transcription_task(
    self,
    media_id: str,
    file_path: str,
    storage_provider: str,
    transcription_provider: str,
    transcription_id: str,
    language: str = "auto",
    correlation_id: Optional[str] = None,
    **_older_fields: Any,  # mensagens enfileiradas por versões anteriores
) -> Optional[Dict[str, Any]]:
    correlation_id = correlation_id or media_id
    logger.info("transcription.task_started", media_id=media_id, transcription_id=transcription_id)

    async def _run() -> None:
        async with AsyncSessionLocal() as session:
            runner = build_transcription_runner(
                session=session,
                event_bus=process_event_bus(),
                storage_provider=storage_provider,
            )
            await runner.execute_transcription(
                transcription_id=UUID(transcription_id),
                media_id=UUID(media_id),
                file_path=file_path,
                storage_provider=storage_provider,
                transcription_provider=transcription_provider,
                language=language,
                final_attempt=is_final_attempt(self),
                correlation_id=correlation_id,
            )

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.error(
            "transcription.task_failed",
            media_id=media_id,
            error=str(exc),
            correlation_id=correlation_id,
            exc_info=True,
        )
        retry_unless_permanent(self, exc)
        raise


@shared_task(name=TASK_MEDIA_SWEEP_STALLED)
def sweep_stalled_processing_task() -> None:
    """Periódica (Celery beat, fila leve): marca como falha as transcrições
    que passaram do prazo."""

    async def _run():
        async with AsyncSessionLocal() as session:
            return await build_stalled_processing_monitor(session, process_event_bus()).sweep()

    failed = asyncio.run(_run())
    if failed:
        logger.warning("stalled_monitor.sweep_done", failed_media=failed)
