"""Application service orchestrating topic modeling workflows."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy import select

from src.media_processing.transcription.domain.transcription import Transcription
from src.text_analysis.topic_modeling.domain.analysis import TopicModelingStatus
from src.text_analysis.topic_modeling.domain.topic_modeling import TopicModelingResult
from src.text_analysis.topic_modeling.infrastructure.logging import (
    StructuredTopicModelingLogger,
)
from src.text_analysis.topic_modeling.infrastructure.metrics import (
    PrometheusTopicModelingMetrics,
)
from src.text_analysis.topic_modeling.infrastructure.topic_modeler import (
    TopicModelerRegistry,
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
        topic_modeler_registry: TopicModelerRegistry,
        topic_modeling_repo: TopicModelingRepository,
        text_analysis_service: "TextAnalysisService | None",
        topic_logger: StructuredTopicModelingLogger,
        topic_metrics: PrometheusTopicModelingMetrics,
    ) -> None:
        self.modelers = topic_modeler_registry
        self.repo = topic_modeling_repo
        self.text_analysis_service = text_analysis_service
        self.logger = topic_logger
        self.metrics = topic_metrics

    async def request_topic_analysis(
        self,
        *,
        media_id: Optional[UUID] = None,
        transcription_id: Optional[UUID] = None,
        text_content: str,
        provider: str,
        language: str,
    ) -> Dict[str, Any]:
        """Schedule a topic modeling task to run asynchronously."""
        if self.text_analysis_service is None:
            logger.warning(
                "topic_modeling.request.unavailable",
                media_id=str(media_id) if media_id else None,
                reason="text_analysis_service_missing",
            )
            raise RuntimeError("TextAnalysisService is not configured")

        transcription = await self._resolve_transcription(
            media_id=media_id,
            transcription_id=transcription_id,
        )
        resolved_media = getattr(transcription, "media_id", None)
        resolved_media_uuid = _ensure_uuid(resolved_media) if resolved_media else None
        resolved_provider = self.modelers.resolve_name(provider)
        logger.info(
            "topic_modeling.request.started",
            media_id=str(resolved_media_uuid) if resolved_media_uuid else None,
            provider=resolved_provider,
        )

        try:
            task_result = await self.text_analysis_service.schedule_topic_modeling_task(
                transcription_id=str(transcription.id),
                text_content=text_content,
                provider=resolved_provider,
                language=language,
            )

            logger.info(
                "topic_modeling.request.completed",
                media_id=str(resolved_media_uuid) if resolved_media_uuid else None,
                task_id=task_result.get("task_id"),
            )
            return {
                "success": True,
                "media_id": str(resolved_media_uuid) if resolved_media_uuid else None,
                "task_id": task_result.get("task_id"),
                "message": "Topic analysis task scheduled successfully",
            }
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error(
                "topic_modeling.request.failed",
                media_id=str(resolved_media_uuid) if resolved_media_uuid else None,
                error=str(exc),
            )
            raise

    async def analyze_topics(
        self,
        *,
        media_id: Optional[UUID] = None,
        transcription_id: Optional[UUID] = None,
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

        transcription = await self._resolve_transcription(
            media_id=media_id,
            transcription_id=transcription_id,
        )
        transcription_uuid = _ensure_uuid(transcription.id)
        resolved_media_uuid = _ensure_uuid(transcription.media_id)
        text_payload = text_content or getattr(transcription, "text", "") or getattr(transcription, "content", "")
        resolved_provider = self.modelers.resolve_name(provider)
        modeler = self.modelers.get(resolved_provider)
        logger.info(
            "topic_modeling.analyze.started",
            media_id=str(resolved_media_uuid),
            transcription_id=str(transcription_uuid),
            provider=resolved_provider,
        )

        async with self.repo.db.begin():
            existing = await self.repo.get_by_transcription_id(transcription_uuid)
            if existing is None:
                result = TopicModelingResult.create(
                    transcription_id=transcription_uuid,
                    provider=resolved_provider,
                )
                self.repo.db.add(result)
            else:
                result = existing
                result.provider = resolved_provider
                result.status = TopicModelingStatus.PROCESSING
                result.error_message = None
                result.processed_at = None
            result_id = result.id
        await self.repo.db.refresh(result)
        setattr(result, "media_id", resolved_media_uuid)

        try:
            topics_payload = await modeler.model_topics(
                text_content=text_payload,
                language=language,
                options=options or {},
            )

            async with self.repo.db.begin():
                assert result_id is not None
                result = await self.repo.get_by_id(result_id)
                if result is None:
                    result = TopicModelingResult.create(
                        transcription_id=transcription_uuid,
                        provider=resolved_provider,
                    )
                    self.repo.db.add(result)
                result.mark_as_completed(topics_payload or {})
            await self.repo.db.refresh(result)
            setattr(result, "media_id", resolved_media_uuid)

            if isinstance(result.topics, dict):
                extracted = result.topics.get("topics")
                if isinstance(extracted, list):
                    num_topics = len(extracted)

            logger.info(
                "topic_modeling.analyze.completed",
                media_id=str(resolved_media_uuid),
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
                    result = TopicModelingResult.create(
                        transcription_id=transcription_uuid,
                        provider=resolved_provider,
                    )
                    self.repo.db.add(result)
                result.mark_as_failed(str(exc))
            logger.error(
                "topic_modeling.analyze.failed",
                media_id=str(resolved_media_uuid),
                error=str(exc),
            )
            raise
        finally:
            duration = time.perf_counter() - started_at
            await self.logger.log_operation(
                operation="analyze",
                media_id=str(resolved_media_uuid),
                provider=resolved_provider,
                success=success,
                duration=duration,
                error=error,
            )
            await self.metrics.record_operation(
                operation="analyze",
                provider=resolved_provider,
                duration=duration,
                success=success,
                input_text_length_chars=len(text_content),
                num_topics=num_topics,
            )

    def analyze_topics_sync(
        self,
        *,
        media_id: Optional[UUID] = None,
        transcription_id: Optional[UUID] = None,
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
        transcription = self._resolve_transcription_sync(
            media_id=media_id,
            transcription_id=transcription_id,
        )
        transcription_uuid = _ensure_uuid(transcription.id)
        resolved_media_uuid = _ensure_uuid(transcription.media_id)
        text_payload = text_content or getattr(transcription, "text", "") or getattr(transcription, "content", "")
        resolved_provider = self.modelers.resolve_name(provider)
        modeler = self.modelers.get(resolved_provider)
        logger.info(
            "topic_modeling.analyze.started_sync",
            media_id=str(resolved_media_uuid),
            transcription_id=str(transcription_uuid),
            provider=resolved_provider,
        )

        # Use sync operations for the database transactions
        existing = self.repo.get_by_transcription_id_sync(transcription_uuid)
        if existing is None:
            result = TopicModelingResult.create(transcription_id=transcription_uuid, provider=resolved_provider)
            result = self.repo.add_sync(result)
        else:
            result = existing
            result.provider = resolved_provider
            result.status = TopicModelingStatus.PROCESSING
            result.error_message = None
            result.processed_at = None
            result = self.repo.update_sync(result)
        result_id = result.id
        setattr(result, "media_id", resolved_media_uuid)

        try:
            topics_payload = modeler.model_topics_sync(
                text_content=text_payload,
                language=language,
                options=options or {},
            )

            # Ensure the result is properly loaded and updated
            result = self.repo.get_by_id_sync(result_id) if result_id else None
            if result is None:
                result = TopicModelingResult.create(transcription_id=transcription_uuid, provider=resolved_provider)
                result = self.repo.add_sync(result)
            result.mark_as_completed(topics_payload or {})
            result = self.repo.update_sync(result)
            setattr(result, "media_id", resolved_media_uuid)

            if isinstance(result.topics, dict):
                extracted = result.topics.get("topics")
                if isinstance(extracted, list):
                    num_topics = len(extracted)

            logger.info(
                "topic_modeling.analyze.completed_sync",
                media_id=str(resolved_media_uuid),
                topics=num_topics,
            )
            success = True
            return result
        except Exception as exc:  # pragma: no cover - defensive update
            error = exc
            result = self.repo.get_by_id_sync(result_id) if result_id else None
            if result is None:
                result = TopicModelingResult.create(transcription_id=transcription_uuid, provider=resolved_provider)
                result = self.repo.add_sync(result)
            result.mark_as_failed(str(exc))
            result = self.repo.update_sync(result)
            logger.error(
                "topic_modeling.analyze.failed_sync",
                media_id=str(resolved_media_uuid),
                error=str(exc),
            )
            raise
        finally:
            duration = time.perf_counter() - started_at
            # Use sync logging if available
            if hasattr(self.logger, 'log_operation_sync'):
                self.logger.log_operation_sync(
                    operation="analyze",
                    media_id=str(resolved_media_uuid),
                    provider=resolved_provider,
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
                    provider=resolved_provider,
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

    def available_providers(self) -> List[str]:
        """Expose lista de providers para UI/admin endpoints."""
        return self.modelers.available()

    async def _resolve_transcription(
        self,
        *,
        media_id: Optional[UUID],
        transcription_id: Optional[UUID],
    ) -> Transcription:
        if not media_id and not transcription_id:
            raise ValueError("Either media_id or transcription_id must be provided")

        stmt = select(Transcription)
        if transcription_id:
            stmt = stmt.where(Transcription.id == _ensure_uuid(transcription_id))
        else:
            stmt = stmt.where(Transcription.media_id == _ensure_uuid(media_id))

        result = await self.repo.db.execute(stmt)
        transcription = result.scalar_one_or_none()
        if transcription is None:
            raise ValueError("Transcription not found")
        return transcription

    def _resolve_transcription_sync(
        self,
        *,
        media_id: Optional[UUID],
        transcription_id: Optional[UUID],
    ) -> Transcription:
        if not media_id and not transcription_id:
            raise ValueError("Either media_id or transcription_id must be provided")

        stmt = select(Transcription)
        if transcription_id:
            stmt = stmt.where(Transcription.id == _ensure_uuid(transcription_id))
        else:
            stmt = stmt.where(Transcription.media_id == _ensure_uuid(media_id))

        result = self.repo.db.execute(stmt)
        transcription = result.scalar_one_or_none()
        if transcription is None:
            raise ValueError("Transcription not found")
        return transcription


__all__ = ["TopicModelingService"]
