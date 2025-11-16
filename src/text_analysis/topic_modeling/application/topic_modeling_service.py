"""Application service orchestrating topic modeling workflows."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID

import structlog

from src.text_analysis.topic_modeling.domain.analysis import TopicModelingStatus
from src.text_analysis.topic_modeling.domain.topic_modeling import TopicModelingResult
from src.text_analysis.topic_modeling.infrastructure.logging import (
    StructuredTopicModelingLogger,
)
from src.text_analysis.topic_modeling.infrastructure.metrics import (
    PrometheusTopicModelingMetrics,
)
from src.text_analysis.topic_modeling.infrastructure.topic_modeler import (
    BERTopicModeler,
)
from src.text_analysis.topic_modeling.infrastructure.topic_modeling_repository import (
    TopicModelingRepository,
)

if TYPE_CHECKING:
    from src.text_analysis.application.services import TextAnalysisService

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
        text_analysis_service: "TextAnalysisService | None",
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
        if self.text_analysis_service is None:
            logger.warning(
                "topic_modeling.request.unavailable",
                media_id=str(media_id),
                reason="text_analysis_service_missing",
            )
            raise RuntimeError("TextAnalysisService is not configured")

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
        num_topics = 0
        success = False
        error: Optional[Exception] = None
        result_id: Optional[UUID] = None
        logger.info(
            "topic_modeling.analyze.started",
            media_id=str(media_id),
            provider=provider,
        )

        async with self.repo.db.begin():
            existing = await self.repo.get_by_media_id(media_id)
            if existing is None:
                result = TopicModelingResult.create(media_id=media_id, provider=provider)
                self.repo.db.add(result)
            else:
                result = existing
                result.provider = provider
                result.status = TopicModelingStatus.PROCESSING
                result.error_message = None
                result.processed_at = None
            result_id = result.id
        await self.repo.db.refresh(result)

        try:
            topics_payload = await self.modeler.model_topics(
                text_content=text_content,
                language=language,
                options=options or {},
            )

            async with self.repo.db.begin():
                assert result_id is not None
                result = await self.repo.get_by_id(result_id)
                if result is None:
                    result = TopicModelingResult.create(media_id=media_id, provider=provider)
                    self.repo.db.add(result)
                result.mark_as_completed(topics_payload or {})
            await self.repo.db.refresh(result)

            if isinstance(result.topics, dict):
                extracted = result.topics.get("topics")
                if isinstance(extracted, list):
                    num_topics = len(extracted)

            logger.info(
                "topic_modeling.analyze.completed",
                media_id=str(media_id),
                topics=num_topics,
            )
            success = True
            return result
        except Exception as exc:  # pragma: no cover - defensive update
            error = exc
            async with self.repo.db.begin():
                if result_id is not None:
                    result = await self.repo.get_by_id(result_id)
                else:
                    result = None
                if result is None:
                    result = TopicModelingResult.create(media_id=media_id, provider=provider)
                    self.repo.db.add(result)
                result.mark_as_failed(str(exc))
            logger.error(
                "topic_modeling.analyze.failed",
                media_id=str(media_id),
                error=str(exc),
            )
            raise
        finally:
            duration = time.perf_counter() - started_at
            await self.logger.log_operation(
                operation="analyze",
                media_id=str(media_id),
                provider=provider,
                success=success,
                duration=duration,
                error=error,
            )
            await self.metrics.record_operation(
                operation="analyze",
                provider=provider,
                duration=duration,
                success=success,
                input_text_length_chars=len(text_content),
                num_topics=num_topics,
            )

    def analyze_topics_sync(
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
        num_topics = 0
        success = False
        error: Optional[Exception] = None
        result_id: Optional[UUID] = None
        logger.info(
            "topic_modeling.analyze.started_sync",
            media_id=str(media_id),
            provider=provider,
        )

        # Use sync operations for the database transactions
        existing = self.repo.get_by_media_id_sync(media_id)
        if existing is None:
            result = TopicModelingResult.create(media_id=media_id, provider=provider)
            result = self.repo.add_sync(result)
        else:
            result = existing
            result.provider = provider
            result.status = TopicModelingStatus.PROCESSING
            result.error_message = None
            result.processed_at = None
            result = self.repo.update_sync(result)
        result_id = result.id

        try:
            topics_payload = self.modeler.model_topics_sync(
                text_content=text_content,
                language=language,
                options=options or {},
            ) if hasattr(self.modeler, 'model_topics_sync') else self.modeler.model_topics(
                text_content=text_content,
                language=language,
                options=options or {},
            )

            # Ensure the result is properly loaded and updated
            result = self.repo.get_by_id_sync(result_id) if result_id else None
            if result is None:
                result = TopicModelingResult.create(media_id=media_id, provider=provider)
                result = self.repo.add_sync(result)
            result.mark_as_completed(topics_payload or {})
            result = self.repo.update_sync(result)

            if isinstance(result.topics, dict):
                extracted = result.topics.get("topics")
                if isinstance(extracted, list):
                    num_topics = len(extracted)

            logger.info(
                "topic_modeling.analyze.completed_sync",
                media_id=str(media_id),
                topics=num_topics,
            )
            success = True
            return result
        except Exception as exc:  # pragma: no cover - defensive update
            error = exc
            result = self.repo.get_by_id_sync(result_id) if result_id else None
            if result is None:
                result = TopicModelingResult.create(media_id=media_id, provider=provider)
                result = self.repo.add_sync(result)
            result.mark_as_failed(str(exc))
            result = self.repo.update_sync(result)
            logger.error(
                "topic_modeling.analyze.failed_sync",
                media_id=str(media_id),
                error=str(exc),
            )
            raise
        finally:
            duration = time.perf_counter() - started_at
            # Use sync logging if available
            if hasattr(self.logger, 'log_operation_sync'):
                self.logger.log_operation_sync(
                    operation="analyze",
                    media_id=str(media_id),
                    provider=provider,
                    success=success,
                    duration=duration,
                    error=error,
                )
            else:
                # Skip logging if no sync method available in Celery context
                pass
            
            # Use sync metrics if available
            if hasattr(self.metrics, 'record_operation_sync'):
                self.metrics.record_operation_sync(
                    operation="analyze",
                    provider=provider,
                    duration=duration,
                    success=success,
                    input_text_length_chars=len(text_content),
                    num_topics=num_topics,
                )
            else:
                # Skip metrics recording if no sync method available in Celery context
                pass

    async def get_topic_modeling_result(
        self, media_id: UUID | str
    ) -> Optional[TopicModelingResult]:
        """Return the persisted topic modeling result for a media item."""
        media_uuid = _ensure_uuid(media_id)
        return await self.repo.get_by_media_id(media_uuid)


__all__ = ["TopicModelingService"]
