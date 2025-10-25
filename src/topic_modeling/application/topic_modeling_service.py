# src/topic_modeling/application/topic_modeling_service.py
"""
Consolidated Topic Modeling Service.
"""
import structlog
from typing import Dict, Any, Optional
from uuid import UUID
import time

from src.topic_modeling.domain.topic_modeling import TopicModelingResult
from src.topic_modeling.infrastructure.topic_modeling_repository import TopicModelingRepository
from src.topic_modeling.infrastructure.topic_modeler import BERTopicModeler
from src.topic_modeling.infrastructure.task_scheduler import CeleryTopicModelingTaskScheduler
from src.topic_modeling.infrastructure.logging import StructuredTopicModelingLogger
from src.topic_modeling.infrastructure.metrics import PrometheusTopicModelingMetrics

logger = structlog.get_logger(__name__)


class TopicModelingService:
    """
    Consolidated service for all topic modeling operations.
    """
    
    def __init__(
        self,
        topic_modeler: BERTopicModeler,
        topic_modeling_repo: TopicModelingRepository,
        task_scheduler: CeleryTopicModelingTaskScheduler,
        topic_logger: StructuredTopicModelingLogger,
        topic_metrics: PrometheusTopicModelingMetrics
    ):
        self.modeler = topic_modeler
        self.repo = topic_modeling_repo
        self.task_scheduler = task_scheduler
        self.logger = topic_logger
        self.metrics = topic_metrics

    async def analyze_topics(self, media_id: UUID, text_content: str, provider: str, language: str, options: Optional[Dict[str, Any]] = None) -> TopicModelingResult:
        """Performs topic modeling on text content and saves the result."""
        start_time = time.monotonic()
        success = False
        error = None
        result_id = None
        num_topics = 0

        logger.info("topic_modeling.analyze.started", media_id=str(media_id), provider=provider)
        try:
            # 1. Perform topic modeling
            modeling_data = await self.modeler.model_topics(
                text_content=text_content,
                language=language,
                options=options
            )
            num_topics = modeling_data.get("num_topics", 0)

            # 2. Create or update TopicModelingResult entity
            existing_result = await self.repo.get_by_media_id(media_id)

            if existing_result:
                existing_result.mark_as_completed(modeling_data.get("topics", {}))
                await self.repo.update(existing_result)
                topic_result = existing_result
            else:
                topic_result = TopicModelingResult.create(
                    media_id=media_id,
                    provider=provider
                )
                topic_result.mark_as_completed(modeling_data.get("topics", {}))
                await self.repo.add(topic_result)
            
            result_id = topic_result.id
            success = True

            logger.info("topic_modeling.analyze.completed", media_id=str(media_id), result_id=str(result_id))
            return topic_result

        except Exception as e:
            error = e
            logger.error("topic_modeling.analyze.failed", media_id=str(media_id), error=str(e))
            raise
        finally:
            duration = time.monotonic() - start_time
            await self.logger.log_operation(
                operation="analyze_topics",
                media_id=str(media_id),
                provider=provider,
                success=success,
                duration=duration,
                error=error
            )
            await self.metrics.record_operation(
                operation="analyze_topics",
                provider=provider,
                duration=duration,
                success=success,
                input_text_length_chars=len(text_content),
                num_topics=num_topics
            )

    async def request_topic_analysis(self, media_id: UUID, text_content: str, provider: str, language: str) -> Dict[str, Any]:
        """Requests the topic analysis of a text for a given media item by scheduling a task."""
        logger.info("topic_modeling.request.started", media_id=str(media_id), provider=provider)
        try:
            # In a real scenario, this would schedule an async task.
            # For now, we'll call the analysis directly.
            topic_result = await self.analyze_topics(media_id, text_content, provider, language)
            
            logger.info("topic_modeling.request.completed", media_id=str(media_id), result_id=str(topic_result.id))
            return {
                "success": True,
                "media_id": str(media_id),
                "result_id": str(topic_result.id),
                "message": "Topic analysis completed directly (or scheduled)"
            }
        except Exception as e:
            logger.error("topic_modeling.request.failed", media_id=str(media_id), error=str(e))
            raise

    async def get_topic_modeling_result(self, media_id: UUID) -> Optional[TopicModelingResult]:
        """Retrieves a topic modeling result by its associated media ID."""
        return await self.repo.get_by_media_id(media_id)

    async def get_topic_modeling_result_by_id(self, result_id: UUID) -> Optional[TopicModelingResult]:
        """Retrieves a topic modeling result by its ID."""
        return await self.repo.get_by_id(result_id)