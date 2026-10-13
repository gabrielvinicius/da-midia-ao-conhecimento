"""Tarefa Celery da análise (camada de montagem).

A tarefa recebe o texto pronto pela fila, monta o serviço com o barramento do
processo e anuncia a falha definitiva (AnalysisFailed); o sucesso é anunciado
pelo próprio serviço (AnalysisCompleted).
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from src.shared.application.event_bus import SupportsEventBus
from src.shared.domain.events import AnalysisFailed
from src.shared.domain.value_objects.identifiers import parse_id, parse_media_id
from src.shared.events.integration_events import TASK_TEXT_ANALYSIS_ANALYZE
from src.shared.infrastructure.config.settings import settings
from src.shared.infrastructure.database.db import AsyncSessionLocal
from src.shared.infrastructure.messaging.process_bus import process_event_bus
from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.shared.infrastructure.tasks.retry import (
    PIPELINE_MAX_RETRIES,
    TRANSIENT_ERRORS,
    is_final_attempt,
    is_transient,
)
from src.text_analysis.application.dtos import AnalyzeTextCommand
from src.text_analysis.domain.entities.analysis import AnalysisReviewedError, AnalysisSourceChangedError
from src.text_analysis.infrastructure.dependencies.builders import build_text_analysis_service

logger = get_logger(__name__)

# Ao vencer o limite brando, a tarefa anuncia a falha; o rígido, dois minutos
# depois, encerra o processo se ela não parar (código nativo na GPU).
ANALYSIS_SOFT_LIMIT_SECONDS = int(settings.analysis_time_limit_minutes * 60)
ANALYSIS_HARD_LIMIT_SECONDS = ANALYSIS_SOFT_LIMIT_SECONDS + 120
TIME_LIMIT_MESSAGE = "A análise passou do tempo máximo e foi interrompida."


def analyze_command(payload: Dict[str, Any]) -> AnalyzeTextCommand:
    media_id = parse_media_id(payload.get("media_id"))
    transcription_id = parse_id(payload.get("transcription_id"))
    return AnalyzeTextCommand(
        media_id=media_id,
        document_id=transcription_id or media_id,
        text_content=payload.get("text_content") or "",
        transcription_id=transcription_id,
        user_id=parse_id(payload.get("user_id")),
        language=payload.get("language"),
        correlation_id=payload.get("correlation_id"),
    )


async def _analyze(payload: Dict[str, Any], bus: SupportsEventBus) -> Dict[str, Any]:
    async with AsyncSessionLocal() as session:
        service = build_text_analysis_service(session, bus)
        return await service.analyze_text_content(analyze_command(payload))


async def _announce_failure(bus: SupportsEventBus, payload: Dict[str, Any], message: str) -> None:
    """Falha definitiva da análise, para quem reagir (mídia e avisos)."""
    try:
        await bus.publish(
            AnalysisFailed(
                media_id=payload.get("media_id"),
                transcription_id=payload.get("transcription_id"),
                user_id=payload.get("user_id"),
                error_message=message,
                correlation_id=payload.get("correlation_id"),
            )
        )
    except Exception as exc:  # o anúncio não pode esconder a falha original
        logger.warning("text_analysis.failure_event_failed", error=str(exc))


def run_analysis(payload: Dict[str, Any], *, bus: SupportsEventBus, final_attempt: bool) -> Dict[str, Any]:
    """Executa a análise; um erro que não passa sozinho (defeito, dado
    inválido) ou o fim das tentativas é anunciado como falha definitiva."""
    logger.info("text_analysis.task.start", media_id=payload.get("media_id"))
    try:
        return asyncio.run(_analyze(payload, bus))
    except (AnalysisReviewedError, AnalysisSourceChangedError) as exc:
        logger.info("text_analysis.request_ignored", media_id=payload.get("media_id"), reason=str(exc))
        return {}
    except SoftTimeLimitExceeded:
        asyncio.run(_announce_failure(bus, payload, TIME_LIMIT_MESSAGE))
        raise
    except Exception as exc:
        if final_attempt or not is_transient(exc):
            asyncio.run(_announce_failure(bus, payload, str(exc)))
        raise


@shared_task(
    bind=True,
    name=TASK_TEXT_ANALYSIS_ANALYZE,
    autoretry_for=TRANSIENT_ERRORS,
    retry_backoff=True,
    max_retries=PIPELINE_MAX_RETRIES,
    soft_time_limit=ANALYSIS_SOFT_LIMIT_SECONDS,
    time_limit=ANALYSIS_HARD_LIMIT_SECONDS,
)
def analyze_task(self, **payload: Any) -> None:
    run_analysis(payload, bus=process_event_bus(), final_attempt=is_final_attempt(self))


__all__ = ["analyze_task", "run_analysis"]
