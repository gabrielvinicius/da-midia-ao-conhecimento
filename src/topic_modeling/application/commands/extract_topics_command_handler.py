# src/topic_modeling/application/commands/extract_topics_command_handler.py
"""
Extract topics command handler following SOLID principles.
"""
import structlog

from src.topic_modeling.domain.topic_modeling import TopicModelingResult
from src.topic_modeling.domain.interfaces import TopicModelingOrchestrator
from src.media_management.application.queries.media_queries import MediaQueries
from src.topic_modeling.application.commands.extract_topics_command import ExtractTopicsCommand

logger = structlog.get_logger(__name__)


class ExtractTopicsCommandHandler:
    """
    Command handler for extracting topics following SOLID principles.
    SRP: Only handles command processing and delegation.
    DIP: Depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        orchestrator: TopicModelingOrchestrator,
        media_queries: MediaQueries
    ):
        self._orchestrator = orchestrator
        self._media_queries = media_queries

    async def handle(self, command: ExtractTopicsCommand) -> TopicModelingResult:
        """Handle topic modeling command."""
        logger.info(
            "topic_modeling.command.extract_started",
            media_id=command.media_id,
            provider=command.provider
        )

        try:
            # Get media information for language and user context
            media = await self._media_queries.get_by_id(command.media_id)
            if not media:
                raise ValueError(f"Media with id {command.media_id} not found.")
            
            # Determine language
            language = getattr(media, 'language', None) or "en"
            if not language or language == "unknown":
                language = "en"  # Default to English
            
            # Get user ID for notifications
            user_id = str(media.user_id)
            
            # Delegate to orchestrator (follows DIP)
            result = await self._orchestrator.process_topic_modeling(
                media_id=command.media_id,
                text_content=command.text_content,
                language=language,
                provider=command.provider,
                user_id=user_id,
                num_topics=5  # Default number of topics
            )

            logger.info(
                "topic_modeling.command.extract_completed",
                media_id=command.media_id,
                result_id=str(result.id),
                num_topics=len(result.topics.get("topics", []))
            )
            
            return result

        except Exception as e:
            logger.error(
                "topic_modeling.command.extract_failed",
                media_id=command.media_id,
                error=str(e)
            )
            raise
