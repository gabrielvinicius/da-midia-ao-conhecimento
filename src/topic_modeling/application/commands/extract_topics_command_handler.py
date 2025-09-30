# src/topic_modeling/application/commands/extract_topics_command_handler.py
import structlog

from src.topic_modeling.domain.topic_modeling import TopicModelingResult
from src.topic_modeling.infrastructure.topic_modeling_repository import TopicModelingRepository
from src.topic_modeling.infrastructure.dependencies import TopicServiceFactory
from .extract_topics_command import ExtractTopicsCommand

logger = structlog.get_logger(__name__)


class ExtractTopicsCommandHandler:
    def __init__(
        self,
        topic_service_factory: TopicServiceFactory,
        repository: TopicModelingRepository,
    ):
        self.topic_service_factory = topic_service_factory
        self.repository = repository

    async def handle(self, command: ExtractTopicsCommand) -> TopicModelingResult:
        """Handles the topic modeling process."""
        logger.info("topic_modeling.started", media_id=command.media_id, provider=command.provider)

        try:
            service = self.topic_service_factory(command.provider)
            
            # The service method is synchronous, so we run it in a thread to avoid blocking
            # topics = await asyncio.to_thread(service.extract_topics, command.text_content)
            # For simplicity in this step, we call it directly. In a real-world high-concurrency
            # scenario, `to_thread` would be essential.
            topics = service.extract_topics(command.text_content)

            result = TopicModelingResult(
                media_id=command.media_id,
                topics=topics
            )

            saved_result = await self.repository.save(result)

            logger.info("topic_modeling.completed", media_id=command.media_id)
            return saved_result

        except Exception as e:
            logger.error("topic_modeling.failed", media_id=command.media_id, error=str(e))
            raise
