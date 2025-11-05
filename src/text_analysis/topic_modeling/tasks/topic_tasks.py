# src/topic_modeling/tasks/topic_tasks.py
import asyncio

import structlog
from celery import shared_task
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from src.text_analysis.topic_modeling.infrastructure.dependencies import (
    create_topic_modeling_service,
)

# Import dependencies for manual construction
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.infrastructure.media_repository import MediaRepository
from src.shared.infrastructure.database import get_db
from src.text_analysis.application.schemas import TopicExtractionTaskPayload
from src.text_analysis.topic_modeling.infrastructure.topic_modeling_repository import (
    TopicModelingRepository,
)

logger = structlog.get_logger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def extract_topics_task(self, media_id: str, text_content: str, provider: str = "sklearn_lda"):
    """Celery task to trigger the topic modeling pipeline."""
    try:
        payload = TopicExtractionTaskPayload.model_validate(
            {
                "media_id": media_id,
                "text_content": text_content,
                "provider": provider,
            }
        )
    except ValidationError as exc:
        logger.error(
            "topic_modeling.task_invalid_payload_legacy",
            media_id=media_id,
            errors=exc.errors(),
        )
        return None

    try:
        # The language is no longer passed as an argument
        return asyncio.run(_run_topic_modeling(payload))
    except Exception as e:
        logger.error(f"Error in topic modeling task for media {media_id}: {str(e)}", exc_info=True)
        return None

async def _run_topic_modeling(payload: TopicExtractionTaskPayload):
    """Helper to run topic modeling logic with dynamic dependency injection."""
    logger.info("topic_modeling.task.started", media_id=str(payload.media_id))
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
            media_id=str(payload.media_id),
            text_content=payload.text_content,
            provider=payload.provider
        )

        try:
            await handler.handle(command)
        except Exception as e:
            logger.error(
                "topic_modeling.task_legacy_failed",
                media_id=str(payload.media_id),
                error=str(e),
                exc_info=True,
            )
            raise
