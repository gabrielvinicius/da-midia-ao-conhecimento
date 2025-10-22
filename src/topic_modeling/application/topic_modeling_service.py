# src/topic_modeling/application/topic_modeling_service.py
import structlog
from typing import Dict, Any, Optional
from uuid import UUID

from src.topic_modeling.domain.interfaces import (
    ITopicModeler,
    ITopicModelingRepository,
    ITopicModelingTaskScheduler,
    TopicModelingOperationLogger,
    TopicModelingMetrics
)
from src.topic_modeling.domain.topic_modeling import TopicModelingResult # Importar a entidade

logger = structlog.get_logger(__name__)


class TopicModelingService:
    """Application service for orchestrating topic modeling operations."""

    def __init__(
        self,
        topic_modeler: ITopicModeler,
        topic_modeling_repo: ITopicModelingRepository,
        task_scheduler: ITopicModelingTaskScheduler,
        topic_logger: TopicModelingOperationLogger,
        topic_metrics: TopicModelingMetrics
    ):
        self.topic_modeler = topic_modeler
        self.topic_modeling_repo = topic_modeling_repo
        self.task_scheduler = task_scheduler
        self.topic_logger = topic_logger
        self.topic_metrics = topic_metrics

    async def request_topic_analysis(self, media_id: UUID, text_content: str, provider: str, language: str) -> Dict[str, Any]:
        """Requests the topic analysis of a text for a given media item."""
        logger.info(
            "topic_modeling_service.request_topic_analysis",
            media_id=str(media_id),
            provider=provider,
            language=language
        )
        try:
            # 1. Schedule the topic modeling task
            task_result = await self.task_scheduler.schedule_topic_modeling_task(
                media_id=str(media_id),
                text_content=text_content,
                provider=provider,
                language=language
            )

            logger.info(
                "topic_modeling_service.topic_modeling_scheduled",
                media_id=str(media_id),
                task_id=task_result.get("task_id")
            )
            return {
                "success": True,
                "media_id": str(media_id),
                "task_id": task_result.get("task_id"),
                "message": "Topic modeling task scheduled successfully"
            }
        except Exception as e:
            logger.error(
                "topic_modeling_service.request_topic_analysis_failed",
                media_id=str(media_id),
                error=str(e)
            )
            raise

    async def get_topic_modeling_result(self, media_id: UUID) -> Optional[TopicModelingResult]:
        """Retrieves a topic modeling result by its associated media ID."""
        return await self.topic_modeling_repo.get_by_media_id(media_id)

    async def get_topic_modeling_result_by_id(self, result_id: UUID) -> Optional[TopicModelingResult]:
        """Retrieves a topic modeling result by its ID."""
        return await self.topic_modeling_repo.get_by_id(result_id)
