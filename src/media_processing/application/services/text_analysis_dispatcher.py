"""Dispatcher to route text analysis work via event bus or direct Celery tasks."""

from __future__ import annotations

import os
from enum import Enum
from typing import Any, Dict, Optional

import structlog

from src.shared.domain.events import TextContentReady

logger = structlog.get_logger(__name__)


class TextAnalysisDispatchStrategy(str, Enum):
    AUTO = "auto"       # Prefer event bus; fallback to direct when bus unavailable
    EVENT_BUS = "event_bus"
    DIRECT = "direct"


class TextAnalysisDispatcher:
    """Dispatches TextContentReady exclusively via event bus.

    Acoplamento mínimo: o dispatcher só conhece o bus e o evento. Se o bus
    não estiver disponível, registra log e retorna (não faz fallback direto).
    """

    def __init__(self, *, event_bus: Any | None) -> None:
        self._event_bus = event_bus

    def dispatch(self, *, transcription_id: str, media_id: str, text: str, metadata: Dict[str, Any], correlation_id: Optional[str]) -> None:
        if self._event_bus is None:
            logger.warning(
                "text_analysis.dispatch.bus_unavailable",
                media_id=media_id,
                transcription_id=transcription_id,
            )
            return

        event = TextContentReady(
            media_id=media_id,
            transcription_id=transcription_id,
            text_content=text,
            metadata=metadata,
            correlation_id=correlation_id,
        )

        try:
            if hasattr(self._event_bus, "publish_sync"):
                self._event_bus.publish_sync(event)
            else:
                import asyncio
                asyncio.run(self._event_bus.publish(event))
            logger.info(
                "text_analysis.dispatch.event_bus",
                media_id=media_id,
                transcription_id=transcription_id,
                correlation_id=correlation_id,
            )
        except Exception as exc:  # pragma: no cover
            logger.warning(
                "text_analysis.dispatch.event_bus_failed",
                media_id=media_id,
                transcription_id=transcription_id,
                error=str(exc),
            )

    def _dispatch_direct(
        self,
        text: str,
        media_id: str,
        transcription_id: str,
        metadata: Dict[str, Any],
        correlation_id: Optional[str],
    ) -> None:
        try:
            from src.text_analysis.tasks import (
                summarize_task,
                sentiment_task,
                topic_modeling_task,
            )
        except Exception as exc:  # pragma: no cover
            logger.error(
                "text_analysis.dispatch.direct_import_failed",
                error=str(exc),
                media_id=media_id,
                transcription_id=transcription_id,
            )
            return

        base_payload: Dict[str, Any] = {
            "text": text,
            "media_id": media_id,
            "transcription_id": transcription_id,
            "language": metadata.get("language"),
            "correlation_id": correlation_id,
        }

        jobs = [
            (summarize_task, {**base_payload, "provider": metadata.get("summarization_provider")}, "summarization"),
            (sentiment_task, {**base_payload, "provider": metadata.get("sentiment_provider")}, "sentiment"),
            (topic_modeling_task, {**base_payload, "provider": metadata.get("topic_provider")}, "topic_modeling"),
        ]

        for task_fn, payload, name in jobs:
            try:
                if hasattr(task_fn, "delay"):
                    task_fn.delay(payload)
                else:
                    task_fn(payload)
                logger.info(
                    "text_analysis.dispatch.direct_enqueued",
                    media_id=media_id,
                    transcription_id=transcription_id,
                    task=name,
                )
            except Exception as exc:  # pragma: no cover
                logger.error(
                    "text_analysis.dispatch.direct_failed",
                    media_id=media_id,
                    transcription_id=transcription_id,
                    task=name,
                    error=str(exc),
                )


__all__ = ["TextAnalysisDispatcher", "TextAnalysisDispatchStrategy"]
