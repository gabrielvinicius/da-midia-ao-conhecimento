"""Celery tasks for text analysis (lightweight wrappers)."""

from __future__ import annotations

import logging
import asyncio
import time
from typing import Any, Dict
from types import SimpleNamespace

try:
    from celery import shared_task
except Exception:  # pragma: no cover - celery optional
    shared_task = None

from .application.service import TextAnalysisService
from src.shared.infrastructure.database import get_sync_session
from src.shared.event_bus_factory import get_event_bus
from .bootstrap import build_text_analysis_module
from src.shared.events.integration_events import (
    TASK_TEXT_ANALYSIS_ANALYZE,
    TASK_TEXT_ANALYSIS_SUMMARIZE,
    TASK_TEXT_ANALYSIS_SENTIMENT,
    TASK_TEXT_ANALYSIS_TOPIC_MODELING,
)

logger = logging.getLogger(__name__)


module_cache = None


async def _get_service_async() -> TextAnalysisService:
    global module_cache
    if module_cache is None:
        # Use sync session for initialization logic that requires DB access
        with get_sync_session() as session:
            # Manually instantiate dependencies required for cross-module access in worker context
            from src.media_processing.transcription.infrastructure.transcription_repository import TranscriptionRepository
            from src.media_processing.transcription.application.queries import TranscriptionQueries
            
            transcription_repo = TranscriptionRepository(session)
            transcription_queries = TranscriptionQueries(transcription_repo)

            module = await build_text_analysis_module(
                session=session,
                transcription_queries=transcription_queries
            )
            module_cache = SimpleNamespace(service=module.service)
    return module_cache.service


async def _async_task_body(payload: Dict[str, Any], op_name: str) -> Dict[str, Any]:
    logger.info("text_analysis.task.start", extra={"payload_keys": list(payload.keys())})
    
    # Get service (awaiting async bootstrap if needed)
    service = await _get_service_async()
    
    if getattr(service, "event_bus", None) is None:
        service.event_bus = get_event_bus()
        
    # Propagate media_id into metrics labels when supported
    if hasattr(service._metrics, "set_context"):
        service._metrics.set_context(payload.get("media_id"), payload.get("user_id"))
        
    correlation_id = payload.get("correlation_id") or payload.get("media_id") or "n/a"
    start = time.perf_counter()
    success = False
    
    try:
        if op_name == "summarization":
            result = await service.schedule_summarization_task(
                media_id=payload.get("media_id"),
                transcription_id=payload.get("transcription_id"),
                text_content=payload.get("text") or payload.get("text_content"),
                segments=payload.get("segments"),
                language=payload.get("language"),
                provider=payload.get("provider"),
                options=payload,
            )
        elif op_name == "sentiment":
            result = await service.schedule_sentiment_analysis_task(
                media_id=payload.get("media_id"),
                transcription_id=payload.get("transcription_id"),
                text=payload.get("text") or payload.get("text_content"),
                segments=payload.get("segments"),
                language=payload.get("language"),
                provider=payload.get("provider"),
                options=payload,
            )
        elif op_name == "topic_modeling":
            result = await service.schedule_topic_modeling_task(
                media_id=payload.get("media_id"),
                text_content=payload.get("text") or payload.get("text_content"),
                segments=payload.get("segments"),
                language=payload.get("language"),
                provider=payload.get("provider"),
                options=payload,
            )
        else:
            result = await service.analyze_text_content(
                text_content=payload.get("text"),
                segments=payload.get("segments"),
                language=payload.get("language"),
                provider=payload.get("provider"),
                options=payload,
                media_id=payload.get("media_id"),
                transcription_id=payload.get("transcription_id"),
                user_id=payload.get("user_id"),
            )
        
        success = True
        return result
    finally:
        duration = time.perf_counter() - start
        try:
            # Record metrics
            await service._metrics.record_operation(
                operation=op_name,
                duration=duration,
                success=success,
                provider=payload.get("provider"),
            )
            
            # Emit completion events per operation
            if hasattr(service, "event_bus") and service.event_bus is not None:
                from src.shared.events.domain_events import (
                    SummarizationCompleted,
                    SentimentAnalysisCompleted,
                    TopicModelingCompleted,
                )

                base = dict(
                    analysis_id=payload.get("analysis_id", ""),
                    transcription_id=payload.get("transcription_id"),
                    media_id=payload.get("media_id"),
                    provider=payload.get("provider"),
                    status="success" if success else "failure",
                    correlation_id=payload.get("correlation_id"),
                )
                if op_name == "summarization":
                    await service.event_bus.publish(SummarizationCompleted(**base))
                elif op_name == "sentiment":
                    await service.event_bus.publish(SentimentAnalysisCompleted(**base))
                elif op_name == "topic_modeling":
                    await service.event_bus.publish(TopicModelingCompleted(**base))
        except Exception:
            pass


def _task_body(payload: Dict[str, Any], *, op_name: str = "analyze_task") -> Dict[str, Any]:
    # Use asyncio.run to manage the event loop lifecycle for this task execution
    return asyncio.run(_async_task_body(payload, op_name))


if shared_task:

    @shared_task(
        name=TASK_TEXT_ANALYSIS_ANALYZE,
        autoretry_for=(Exception,),
        retry_backoff=True,
        max_retries=3,
    )
    def analyze_task(**kwargs) -> Dict[str, Any]:
        # kwargs represents the payload from send_task(kwargs=...)
        return _task_body(kwargs, op_name="analyze_task")

    @shared_task(
        name=TASK_TEXT_ANALYSIS_SUMMARIZE,
        autoretry_for=(Exception,),
        retry_backoff=True,
        max_retries=3,
    )
    def summarize_task(**kwargs) -> Dict[str, Any]:
        return _task_body(kwargs, op_name="summarization")

    @shared_task(
        name=TASK_TEXT_ANALYSIS_SENTIMENT,
        autoretry_for=(Exception,),
        retry_backoff=True,
        max_retries=3,
    )
    def sentiment_task(**kwargs) -> Dict[str, Any]:
        return _task_body(kwargs, op_name="sentiment")

    @shared_task(
        name=TASK_TEXT_ANALYSIS_TOPIC_MODELING,
        autoretry_for=(Exception,),
        retry_backoff=True,
        max_retries=3,
    )
    def topic_modeling_task(**kwargs) -> Dict[str, Any]:
        return _task_body(kwargs, op_name="topic_modeling")

else:
    # Fallback for environments without Celery
    def analyze_task(**kwargs) -> Dict[str, Any]:
        return _task_body(kwargs, op_name="analyze_task")

    def summarize_task(**kwargs) -> Dict[str, Any]:
        return _task_body(kwargs, op_name="summarization")

    def sentiment_task(**kwargs) -> Dict[str, Any]:
        return _task_body(kwargs, op_name="sentiment")

    def topic_modeling_task(**kwargs) -> Dict[str, Any]:
        return _task_body(kwargs, op_name="topic_modeling")


__all__ = [
    "analyze_task",
    "summarize_task",
    "sentiment_task",
    "topic_modeling_task",
]
