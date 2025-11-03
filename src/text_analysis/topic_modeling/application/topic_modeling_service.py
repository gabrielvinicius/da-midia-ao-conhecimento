"""Application service orchestrating topic modeling workflows."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional
from uuid import UUID

import structlog

from src.text_analysis.application.services import TextAnalysisService
from src.text_analysis.topic_modeling.domain.analysis import TopicModelingStatus
from src.text_analysis.topic_modeling.domain.topic_modeling import TopicModelingResult
from src.text_analysis.topic_modeling.infrastructure.logging import (
    StructuredTopicModelingLogger,
)
from src.text_analysis.topic_modeling.infrastructure.metrics import (
    PrometheusTopicModelingMetrics,
)
from src.text_analysis.topic_modeling.infrastructure.topic_modeler import BERTopicModeler
from src.text_analysis.topic_modeling.infrastructure.topic_modeling_repository import (
    TopicModelingRepository,
)

logger = structlog.get_logger(__name__)


def _ensure_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


class TopicModelingService:
    """Coordinates scheduling and execution of topic modeling requests."""

    def __init__(
        self,
        *,
        topic_modeler: BERTopicModeler,
        topic_modeling_repo: TopicModelingRepository,
        text_analysis_service: TextAnalysisService,
        topic_logger: StructuredTopicModelingLogger,
        topic_metrics: PrometheusTopicModelingMetrics,
    ) -> None:
        self.modeler = topic_modeler
        self.repo = topic_modeling_repo
        self.text_analysis_service = text_analysis_service
        self.logger = topic_logger
        self.metrics = topic_metrics

    async def request_topic_analysis(
        self,
        *,
        media_id: UUID,
        text_content: str,
        provider: str,
        language: str,
    ) -> Dict[str, Any]:
        """Schedule a topic modeling task to run asynchronously."""

        logger.info(
            "topic_modeling.request.started",
            media_id=str(media_id),
            provider=provider,
        )
        try:
            task_result = await self.text_analysis_service.schedule_topic_modeling_task(
                media_id=str(media_id),
                text_content=text_content,
                provider=provider,
                language=language,
            )

            logger.info(
                "topic_modeling.request.completed",
                media_id=str(media_id),
                task_id=task_result.get("task_id"),
            )
            return {
                "success": True,
                "media_id": str(media_id),
                "task_id": task_result.get("task_id"),
                "message": "Topic analysis task scheduled successfully",
            }
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "topic_modeling.request.failed",
                media_id=str(media_id),
                error=str(exc),
            )
            raise

    async def analyze_topics(
        self,
        *,
        media_id: UUID,
        text_content: str,
        provider: str,
        language: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> TopicModelingResult:
        """Execute topic modeling synchronously and persist the result."""

        started_at = time.perf_counter()
        logger.info(
            "topic_modeling.analyze.started",
            media_id=str(media_id),
            provider=provider,
        )

        existing = await self.repo.get_by_media_id(media_id)
        if existing is None:
            result = TopicModelingResult.create(media_id=media_id, provider=provider)
            await self.repo.add(result)
        else:
            result = existing
            result.provider = provider
            result.status = TopicModelingStatus.PROCESSING
            result.error_message = None
            result.processed_at = None
            await self.repo.update(result)

        try:
            topics_payload = await self.modeler.model_topics(
                text_content=text_content,
                language=language,
                options=options or {},
            )

            result.mark_as_completed(topics_payload or {})
            await self.repo.update(result)

            num_topics = 0
            if isinstance(result.topics, dict):
                extracted = result.topics.get("topics")
                if isinstance(extracted, list):
                    num_topics = len(extracted)

            await self.metrics.record_operation(
                operation="analyze",
                provider=provider,
                duration=time.perf_counter() - started_at,
                success=True,
                input_text_length_chars=len(text_content),
                num_topics=num_topics,
            )

            logger.info(
                "topic_modeling.analyze.completed",
                media_id=str(media_id),
                topics=num_topics,
            )
            return result
        except Exception as exc:  # pragma: no cover - defensive update
            result.mark_as_failed(str(exc))
            await self.repo.update(result)
            await self.metrics.record_operation(
                operation="analyze",
                provider=provider,
                duration=time.perf_counter() - started_at,
                success=False,
                input_text_length_chars=len(text_content),
                num_topics=0,
            )
            logger.error(
                "topic_modeling.analyze.failed",
                media_id=str(media_id),
                error=str(exc),
            )
            raise

    async def get_topic_modeling_result(
        self, media_id: UUID | str
    ) -> Optional[TopicModelingResult]:
        """Return the persisted topic modeling result for a media item."""

        media_uuid = _ensure_uuid(media_id)
        return await self.repo.get_by_media_id(media_uuid)


__all__ = ["TopicModelingService"]
