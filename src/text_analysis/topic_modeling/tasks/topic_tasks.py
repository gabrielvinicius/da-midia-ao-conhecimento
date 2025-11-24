# src/topic_modeling/tasks/topic_tasks.py
import structlog
from celery import shared_task
from pydantic import ValidationError
from src.text_analysis.topic_modeling.infrastructure.dependencies import (
    create_topic_modeling_service_sync,
)

# Import dependencies for manual construction
from src.media_management.application.queries.media_queries_sync import (
    MediaQueriesSync,
)
from src.media_management.infrastructure.media_repository_sync import (
    MediaRepositorySync,
)
from src.shared.infrastructure.database import get_sync_db
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
        # Use synchronous database session in Celery worker
        with get_sync_db() as db_session:
            return _run_topic_modeling_sync(payload, db_session)
    except Exception as e:
        logger.error(f"Error in topic modeling task for media {media_id}: {str(e)}", exc_info=True)
        return None

def _run_topic_modeling_sync(payload: TopicExtractionTaskPayload, db_session):
    """Synchronous helper to run topic modeling logic with dynamic dependency injection."""
    logger.info("topic_modeling.task.started", media_id=str(payload.media_id))

    # --- Manual Dependency Injection for Celery Task ---
    repository = TopicModelingRepository(db=db_session)  # This should work with sync session now
    service_factory = create_topic_modeling_service_sync  # Use sync version if available

    # The handler now needs MediaQueries to fetch the language
    media_repo = MediaRepositorySync(db=db_session)
    media_queries = MediaQueriesSync(media_repository=media_repo)

    handler = ExtractTopicsCommandHandler(
        topic_service_factory=service_factory,
        repository=repository,
        media_queries=media_queries  # Inject the new dependency
    )

    command = ExtractTopicsCommand(
        media_id=str(payload.media_id),
        text_content=payload.text_content,
        provider=payload.provider
    )

    try:
        # Use sync method if available, otherwise handle async in new event loop
        if hasattr(handler, 'handle_sync'):
            return handler.handle_sync(command)
        else:
            # Fallback: use async method with new event loop
            import asyncio
            try:
                return asyncio.run(handler.handle(command))
            except RuntimeError:
                # If there's already an event loop, use thread-based approach
                import concurrent.futures
                def run_async():
                    return asyncio.run(handler.handle(command))
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async)
                    return future.result()
    except Exception as e:
        logger.error(
            "topic_modeling.task_legacy_failed",
            media_id=str(payload.media_id),
            error=str(e),
            exc_info=True,
        )
        raise
