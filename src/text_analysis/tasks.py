"""Celery tasks para text_analysis (wrappers finos).

Decisão arquitetural:
- Event bus é apenas in-process (não cross-process).
- Integração entre processos acontece via Celery e persistência (DB), não via event bus.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, Optional

try:
    from celery import shared_task
except Exception:  # pragma: no cover - celery optional
    shared_task = None

from src.shared.infrastructure.database.db import AsyncSessionLocal
from src.shared.infrastructure.messaging.event_bus_factory import (
    get_event_bus as build_event_bus,
)
from src.text_analysis.application.dtos import AnalyzeTextCommand
from src.text_analysis.application.services.text_analysis_service import TextAnalysisService
from src.text_analysis.infrastructure.dependencies.providers import get_event_bus
from src.text_analysis.worker_bootstrap import build_text_analysis_service

TASK_TEXT_ANALYSIS_ANALYZE = "text_analysis.analyze"
TASK_TEXT_ANALYSIS_SUMMARIZE = "text_analysis.summarize"
TASK_TEXT_ANALYSIS_SENTIMENT = "text_analysis.sentiment"
TASK_TEXT_ANALYSIS_TOPIC_MODELING = "text_analysis.topic_modeling"

DEFAULT_MAX_RETRIES = 3

logger = logging.getLogger(__name__)

EVENT_BUS = build_event_bus()


def _ensure_event_bus(bus=None):
    return get_event_bus(bus or EVENT_BUS)


async def _build_service(*, session, event_bus) -> TextAnalysisService:
    from src.media_processing.infrastructure.dependencies.transcription_query_adapter import (
        TranscriptionQueryAdapter,
    )
    from src.media_processing.infrastructure.repositories.transcription_repository import (
        TranscriptionRepository,
    )
    from src.text_analysis.infrastructure.repositories.sqlalchemy_analysis_repository import (
        SqlAlchemyAnalysisRepository,
    )

    transcription_repo = TranscriptionRepository(session)
    transcription_queries = TranscriptionQueryAdapter(transcription_repo)
    repository = SqlAlchemyAnalysisRepository(session)

    module = build_text_analysis_service(
        repository=repository,
        event_bus=_ensure_event_bus(event_bus),
        transcription_queries=transcription_queries,
    )
    return module.service


async def _async_task_body(
    payload: Dict[str, Any],
    op_name: str,
    service: TextAnalysisService,
) -> Dict[str, Any]:
    logger.info(
        "text_analysis.task.start",
        extra={"payload_keys": list(payload.keys())},
    )

    start = time.perf_counter()
    success = False

    try:
        media_id: Optional[str] = payload.get("media_id")
        transcription_id: Optional[str] = payload.get("transcription_id")
        user_id: Optional[str] = payload.get("user_id")
        text = payload.get("text") or payload.get("text_content") or ""
        language: Optional[str] = payload.get("language")

        from uuid import UUID

        media_uuid = UUID(str(media_id)) if media_id else None
        transcription_uuid = UUID(str(transcription_id)) if transcription_id else None
        user_uuid = UUID(str(user_id)) if user_id else None

        if media_uuid is None:
            raise ValueError("media_id é obrigatório para análise de texto")

        document_id = transcription_uuid or media_uuid

        command = AnalyzeTextCommand(
            media_id=media_uuid,
            document_id=document_id,
            text_content=text,
            transcription_id=transcription_uuid,
            user_id=user_uuid,
            language=language,
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


async def _notify_final_failure(
    *,
    session,
    payload: Dict[str, Any],
    op_name: str,
    error_message: str,
) -> None:
    user_id = payload.get("user_id")
    if not user_id:
        return

    from uuid import UUID

    from src.notifications.application.services.pipeline_notification_service import (
        PipelineNotificationService,
    )
    from src.notifications.infrastructure.adapters.notification_logger_adapter import (
        NotificationLoggerAdapter,
    )
    from src.notifications.infrastructure.adapters.notification_metrics_adapter import (
        NotificationMetricsAdapter,
    )
    from src.notifications.infrastructure.adapters.notification_repository_adapter import (
        NotificationRepositoryAdapter,
    )
    from src.notifications.infrastructure.adapters.redis_notification_delivery_adapter import (
        RedisNotificationDeliveryAdapter,
    )
    from src.notifications.infrastructure.repositories.notification_repository import (
        NotificationRepository,
    )

    repo = NotificationRepository(db=session)
    service = PipelineNotificationService(
        notification_repo=NotificationRepositoryAdapter(repo),
        delivery=RedisNotificationDeliveryAdapter(),
        notification_logger=NotificationLoggerAdapter(),
        notification_metrics=NotificationMetricsAdapter(),
    )

    await service.notify(
        user_id=UUID(str(user_id)),
        message="Falha ao analisar o texto.",
        correlation_id=payload.get("correlation_id"),
        variables={
            "media_id": payload.get("media_id"),
            "transcription_id": payload.get("transcription_id"),
            "op": op_name,
            "erro": error_message,
            "evento": "TextAnalysisFailed",
        },
    )


def _task_body_with_retry_context(
    payload: Dict[str, Any],
    *,
    op_name: str,
    event_bus=None,
    final_attempt: bool,
) -> Dict[str, Any]:
    async def _run() -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            service = await _build_service(
                session=session,
                event_bus=_ensure_event_bus(event_bus),
            )
            try:
                return await _async_task_body(payload, op_name, service)
            except Exception as exc:
                if final_attempt:
                    try:
                        await _notify_final_failure(
                            session=session,
                            payload=payload,
                            op_name=op_name,
                            error_message=str(exc),
                        )
                    except Exception:
                        pass
                raise

    return asyncio.run(_run())


if shared_task:

    @shared_task(
        bind=True,
        name=TASK_TEXT_ANALYSIS_ANALYZE,
        autoretry_for=(Exception,),
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

    @shared_task(
        bind=True,
        name=TASK_TEXT_ANALYSIS_SUMMARIZE,
        autoretry_for=(Exception,),
        retry_backoff=True,
        max_retries=DEFAULT_MAX_RETRIES,
    )
    def summarize_task(self, event_bus=None, **kwargs) -> Dict[str, Any]:
        final_attempt = (self.request.retries or 0) >= (self.max_retries or 0)
        return _task_body_with_retry_context(
            kwargs,
            op_name="summarization",
            event_bus=event_bus,
            final_attempt=final_attempt,
        )

    @shared_task(
        bind=True,
        name=TASK_TEXT_ANALYSIS_SENTIMENT,
        autoretry_for=(Exception,),
        retry_backoff=True,
        max_retries=DEFAULT_MAX_RETRIES,
    )
    def sentiment_task(self, event_bus=None, **kwargs) -> Dict[str, Any]:
        final_attempt = (self.request.retries or 0) >= (self.max_retries or 0)
        return _task_body_with_retry_context(
            kwargs,
            op_name="sentiment",
            event_bus=event_bus,
            final_attempt=final_attempt,
        )

    @shared_task(
        bind=True,
        name=TASK_TEXT_ANALYSIS_TOPIC_MODELING,
        autoretry_for=(Exception,),
        retry_backoff=True,
        max_retries=DEFAULT_MAX_RETRIES,
    )
    def topic_modeling_task(self, event_bus=None, **kwargs) -> Dict[str, Any]:
        final_attempt = (self.request.retries or 0) >= (self.max_retries or 0)
        return _task_body_with_retry_context(
            kwargs,
            op_name="topic_modeling",
            event_bus=event_bus,
            final_attempt=final_attempt,
        )

else:
    # Fallback for environments without Celery
    def analyze_task(**kwargs) -> Dict[str, Any]:
        return _task_body_with_retry_context(
            kwargs,
            op_name="analyze_task",
            final_attempt=True,
        )

    def summarize_task(**kwargs) -> Dict[str, Any]:
        return _task_body_with_retry_context(
            kwargs,
            op_name="summarization",
            final_attempt=True,
        )

    def sentiment_task(**kwargs) -> Dict[str, Any]:
        return _task_body_with_retry_context(
            kwargs,
            op_name="sentiment",
            final_attempt=True,
        )

    def topic_modeling_task(**kwargs) -> Dict[str, Any]:
        return _task_body_with_retry_context(
            kwargs,
            op_name="topic_modeling",
            final_attempt=True,
        )


__all__ = [
    "analyze_task",
    "summarize_task",
    "sentiment_task",
    "topic_modeling_task",
]

