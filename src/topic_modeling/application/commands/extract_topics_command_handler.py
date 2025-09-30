# src/topic_modeling/application/commands/extract_topics_command_handler.py
import structlog
from typing import List

from src.topic_modeling.domain.topic_modeling import TopicModelingResult
from src.topic_modeling.infrastructure.topic_modeling_repository import TopicModelingRepository
from src.topic_modeling.infrastructure.dependencies import TopicServiceFactory
from src.media_management.application.queries.media_queries import MediaQueries # Import dependency
from .extract_topics_command import ExtractTopicsCommand

logger = structlog.get_logger(__name__)


class ExtractTopicsCommandHandler:
    def __init__(
        self,
        topic_service_factory: TopicServiceFactory,
        repository: TopicModelingRepository,
        media_queries: MediaQueries, # Add dependency
    ):
        self.topic_service_factory = topic_service_factory
        self.repository = repository
        self.media_queries = media_queries

    async def handle(self, command: ExtractTopicsCommand) -> TopicModelingResult:
        """Handles the topic modeling process, now with language awareness."""
        logger.info("topic_modeling.started", media_id=command.media_id, provider=command.provider)

        try:
            # Fetch the media to get its language
            media = await self.media_queries.get_by_id(command.media_id)
            if not media or not media.language:
                # If language is not set, default to English or skip.
                logger.warn("media.language.not_found", media_id=command.media_id, fallback_language="english")
                language = "english"
            else:
                language = media.language

            service = self.topic_service_factory(command.provider)
            
            # Pass the language to the service
            topics = service.extract_topics(command.text_content, language=language)

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
