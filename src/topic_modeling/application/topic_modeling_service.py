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

    async def request_topic_analysis(self, media_id: UUID, text_content: str, provider: str, language: str) -> Dict[str, Any]:
        """Requests the topic analysis of a text for a given media item by scheduling a task."""
        logger.info("topic_modeling.request.started", media_id=str(media_id), provider=provider)
        try:
            task_result = await self.task_scheduler.schedule_topic_modeling_task(
                media_id=str(media_id),
                text_content=text_content,
                provider=provider,
                language=language
            )
            
            logger.info("topic_modeling.request.completed", media_id=str(media_id), task_id=task_result.get("task_id"))
            return {
                "success": True,
                "media_id": str(media_id),
                "task_id": task_result.get("task_id"),
                "message": "Topic analysis task scheduled successfully"
            }
        except Exception as e:
            logger.error("topic_modeling.request.failed", media_id=str(media_id), error=str(e))
            raise