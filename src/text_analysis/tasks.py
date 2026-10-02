"""Celery tasks para text_analysis (wrappers finos).

Decisão arquitetural:
- Event bus é apenas in-process (não cross-process).
- Integração entre processos acontece via Celery e persistência (DB), não via event bus.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any, Dict, Optional

from celery import shared_task

from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.shared.infrastructure.database.db import AsyncSessionLocal
from src.shared.events.integration_events import TASK_TEXT_ANALYSIS_ANALYZE
from src.shared.infrastructure.messaging.process_bus import process_event_bus
from src.shared.infrastructure.tasks.retry import TRANSIENT_ERRORS, is_transient
from src.shared.domain.events import AnalysisFailed
from src.shared.domain.value_objects.identifiers import parse_id, parse_media_id
from src.text_analysis.application.dtos import AnalyzeTextCommand
from src.text_analysis.application.services.text_analysis_service import TextAnalysisService
from src.text_analysis.infrastructure.dependencies.providers import get_event_bus
from src.text_analysis.infrastructure.dependencies.builders import build_text_analysis_service

DEFAULT_MAX_RETRIES = 3

logger = get_logger(__name__)

def _ensure_event_bus(bus=None):
    """Barramento deste processo de worker (ver process_bus), salvo quando informado."""
    return get_event_bus(bus or process_event_bus())


async def _build_service(*, session, event_bus) -> TextAnalysisService:
    return build_text_analysis_service(session, _ensure_event_bus(event_bus))


async def _async_task_body(
    payload: Dict[str, Any],
    op_name: str,
    service: TextAnalysisService,
) -> Dict[str, Any]:
    logger.info(
        "text_analysis.task.start",
        payload_keys=list(payload.keys()),
    )

    start = time.perf_counter()
    success = False

    try:
        media_id: Optional[str] = payload.get("media_id")
        transcription_id: Optional[str] = payload.get("transcription_id")
        user_id: Optional[str] = payload.get("user_id")
        text = payload.get("text") or payload.get("text_content") or ""
        language: Optional[str] = payload.get("language")

        media_uuid = parse_media_id(media_id)
        transcription_uuid = parse_id(transcription_id)
        user_uuid = parse_id(user_id)

        document_id = transcription_uuid or media_uuid

        command = AnalyzeTextCommand(
            media_id=media_uuid,
            document_id=document_id,
            text_content=text,
            transcription_id=transcription_uuid,
            user_id=user_uuid,
            language=language,
            correlation_id=payload.get("correlation_id"),
        )
        result = await service.analyze_text_content(command)
        success = True
        return result
    finally:
        duration = time.perf_counter() - start
        try:
            metrics = getattr(service, "metrics", None)
            if metrics is not None and hasattr(metrics, "record_operation"):
                await metrics.record_operation(
                    operation=op_name,
                    duration=duration,
                    success=success,
                    provider=payload.get("provider"),
                )
        except Exception:
            # best-effort: não quebrar a task por falha de métricas
            pass


async def _announce_failure(event_bus, payload: Dict[str, Any], exc: Exception) -> None:
    """Falha definitiva da análise, para quem reagir (o módulo de avisos avisa o dono)."""
    try:
        await event_bus.publish(
            AnalysisFailed(
                media_id=payload.get("media_id"),
                transcription_id=payload.get("transcription_id"),
                user_id=payload.get("user_id"),
                error_message=str(exc),
                correlation_id=payload.get("correlation_id"),
            )
        )
    except Exception as notify_exc:  # o anúncio não pode esconder a falha original
        logger.warning("text_analysis.failure_event_failed", error=str(notify_exc))


def _task_body_with_retry_context(
    payload: Dict[str, Any],
    *,
    op_name: str,
    event_bus=None,
    final_attempt: bool,
) -> Dict[str, Any]:
    async def _run() -> Dict[str, Any]:
        bus = _ensure_event_bus(event_bus)
        async with AsyncSessionLocal() as session:
            service = await _build_service(session=session, event_bus=bus)
            try:
                # O fim da análise é anunciado pelo serviço (AnalysisCompleted).
                return await _async_task_body(payload, op_name, service)
            except Exception as exc:
                # Erro que não passa sozinho (defeito, dado inválido) não é
                # repetido: esta já é a última tentativa.
                if final_attempt or not is_transient(exc):
                    await _announce_failure(bus, payload, exc)
                raise

    return asyncio.run(_run())


@shared_task(
    bind=True,
    name=TASK_TEXT_ANALYSIS_ANALYZE,
    autoretry_for=TRANSIENT_ERRORS,
    retry_backoff=True,
    max_retries=DEFAULT_MAX_RETRIES,
)
def analyze_task(self, event_bus=None, **kwargs) -> Dict[str, Any]:
    final_attempt = (self.request.retries or 0) >= (self.max_retries or 0)
    return _task_body_with_retry_context(
        kwargs,
        op_name="analyze_task",
        event_bus=event_bus,
        final_attempt=final_attempt,
    )


__all__ = ["analyze_task"]
