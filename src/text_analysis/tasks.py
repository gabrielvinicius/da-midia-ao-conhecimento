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

logger = logging.getLogger(__name__)


module_cache = None


def _build_service_with_session() -> TextAnalysisService:
    with get_sync_session() as session:
        module = asyncio.get_event_loop().run_until_complete(
            build_text_analysis_module(session=session)
        )
    return module.service


def _get_service() -> TextAnalysisService:
    global module_cache
    if module_cache is None:
        module_cache = SimpleNamespace(service=_build_service_with_session())
    return module_cache.service


def _task_body(payload: Dict[str, Any], *, op_name: str = "analyze_task") -> Dict[str, Any]:
    logger.info("text_analysis.task.start", extra={"payload_keys": list(payload.keys())})
    service = _get_service()
    if getattr(service, "event_bus", None) is None:
        service.event_bus = get_event_bus()
    # Propagate media_id into metrics labels when supported
    if hasattr(service._metrics, "set_media_context"):
        service._metrics.set_media_context(payload.get("media_id"))
    loop = asyncio.get_event_loop()
    start = time.perf_counter()
    success = False
    try:
        if op_name == "summarization":
            coro = service.schedule_summarization_task(
                media_id=payload.get("media_id"),
                transcription_id=payload.get("transcription_id"),
                text_content=payload.get("text") or payload.get("text_content", ""),
                segments=payload.get("segments"),
                language=payload.get("language"),
                provider=payload.get("provider"),
                options=payload,
            )
        elif op_name == "sentiment":
            coro = service.schedule_sentiment_analysis_task(
                media_id=payload.get("media_id"),
                transcription_id=payload.get("transcription_id"),
                text=payload.get("text") or payload.get("text_content", ""),
                segments=payload.get("segments"),
                language=payload.get("language"),
                provider=payload.get("provider"),
                options=payload,
            )
        elif op_name == "topic_modeling":
            coro = service.schedule_topic_modeling_task(
                media_id=payload.get("media_id"),
                text_content=payload.get("text") or payload.get("text_content", ""),
                segments=payload.get("segments"),
                language=payload.get("language"),
                provider=payload.get("provider"),
                options=payload,
            )
        else:
            coro = service.analyze_text_content(
                text_content=payload.get("text", ""),
                segments=payload.get("segments"),
                language=payload.get("language"),
                provider=payload.get("provider"),
                options=payload,
                media_id=payload.get("media_id"),
                transcription_id=payload.get("transcription_id"),
                user_id=payload.get("user_id"),
            )

        result = loop.run_until_complete(coro)
        success = True
        return result
    finally:
        duration = time.perf_counter() - start
        try:
            loop.run_until_complete(
                service._metrics.record_operation(
                    operation=op_name,
                    duration=duration,
                    success=success,
                    provider=payload.get("provider"),
                )
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
                    service.event_bus.publish(SummarizationCompleted(**base))
                elif op_name == "sentiment":
                    service.event_bus.publish(SentimentAnalysisCompleted(**base))
                elif op_name == "topic_modeling":
                    service.event_bus.publish(TopicModelingCompleted(**base))
        except Exception:
            pass


if shared_task:

    @shared_task(
        name="text_analysis.analyze",
        autoretry_for=(Exception,),
        retry_backoff=True,
        max_retries=3,
    )
    def analyze_task(payload: Dict[str, Any]) -> Dict[str, Any]:
        return _task_body(payload, op_name="analyze_task")

    @shared_task(
        name="text_analysis.summarize",
        autoretry_for=(Exception,),
        retry_backoff=True,
        max_retries=3,
    )
    def summarize_task(payload: Dict[str, Any]) -> Dict[str, Any]:
        return _task_body(payload, op_name="summarization")

    @shared_task(
        name="text_analysis.sentiment",
        autoretry_for=(Exception,),
        retry_backoff=True,
        max_retries=3,
    )
    def sentiment_task(payload: Dict[str, Any]) -> Dict[str, Any]:
        return _task_body(payload, op_name="sentiment")

    @shared_task(
        name="text_analysis.topic_modeling",
        autoretry_for=(Exception,),
        retry_backoff=True,
        max_retries=3,
    )
    def topic_modeling_task(payload: Dict[str, Any]) -> Dict[str, Any]:
        return _task_body(payload, op_name="topic_modeling")

else:
    # Fallback for environments without Celery
    def analyze_task(payload: Dict[str, Any]) -> Dict[str, Any]:
        return _task_body(payload, op_name="analyze_task")

    def summarize_task(payload: Dict[str, Any]) -> Dict[str, Any]:
        return _task_body(payload, op_name="summarization")

    def sentiment_task(payload: Dict[str, Any]) -> Dict[str, Any]:
        return _task_body(payload, op_name="sentiment")

    def topic_modeling_task(payload: Dict[str, Any]) -> Dict[str, Any]:
        return _task_body(payload, op_name="topic_modeling")


__all__ = [
    "analyze_task",
    "summarize_task",
    "sentiment_task",
    "topic_modeling_task",
]
