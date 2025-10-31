# src/topic_modeling/tasks/topic_tasks.py
import asyncio
import structlog
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.database import get_db
from src.topic_modeling.application.commands.commands import ProcessTopicModelingCommand
from src.topic_modeling.application.commands.handlers import ProcessTopicModelingCommandHandler
from src.topic_modeling.infrastructure.dependencies import create_topic_modeling_service
from src.topic_modeling.infrastructure.topic_modeling_repository import TopicModelingRepository
# Import dependencies for manual construction
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.infrastructure.media_repository import MediaRepository

logger = structlog.get_logger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def extract_topics_task(self, media_id: str, text_content: str, provider: str = "sklearn_lda"):
    """Celery task to trigger the topic modeling pipeline."""
    try:
        # The language is no longer passed as an argument
        return asyncio.run(_run_topic_modeling(media_id, text_content, provider))
    except Exception as e:
        logger.error(f"Error in topic modeling task for media {media_id}: {str(e)}", exc_info=True)
        return None

async def _run_topic_modeling(media_id: str, text_content: str, provider: str):
    """Helper to run topic modeling logic with dynamic dependency injection."""
    logger.info("topic_modeling.task.started", media_id=media_id)
    async for db_session in get_db():
        if not isinstance(db_session, AsyncSession):
            raise TypeError("Expected db_session to be an AsyncSession")

        # --- Manual Dependency Injection for Celery Task ---
        repository = TopicModelingRepository(db=db_session)
        service_factory = create_topic_modeling_service
        
        # The handler now needs MediaQueries to fetch the language
        media_repo = MediaRepository(db=db_session)
        media_queries = MediaQueries(media_repository=media_repo)

        handler = ExtractTopicsCommandHandler(
            topic_service_factory=service_factory,
            repository=repository,
            media_queries=media_queries # Inject the new dependency
        )

        command = ExtractTopicsCommand(
            media_id=media_id,
            text_content=text_content,
            provider=provider
        )

        try:
            await handler.handle(command)
        except Exception as e:
            logger.error(f"Error processing topics for media {media_id}: {str(e)}", exc_info=True)
            raise
