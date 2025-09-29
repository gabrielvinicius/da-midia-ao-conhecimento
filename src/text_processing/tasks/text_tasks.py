# src/text_processing/tasks/text_tasks.py
import asyncio
import structlog
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.database import get_db
from src.shared.events.event_bus import get_event_bus
from src.storage.infrastructure.dependencies import get_storage_service_factory
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.infrastructure.media_repository import MediaRepository
from src.text_processing.application.commands.process_text_command import ProcessTextCommand
from src.text_processing.application.commands.process_text_command_handler import ProcessTextCommandHandler

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_text_task(self, media_id: str, file_path: str, storage_provider: str):
    """Celery task to trigger the text processing (e.g., PDF extraction) pipeline."""
    try:
        return asyncio.run(_run_text_processing(media_id, file_path, storage_provider))
    except Exception as e:
        logger.error(f"Error in text processing task for media {media_id}: {str(e)}", exc_info=True)
        return None


async def _run_text_processing(media_id: str, file_path: str, storage_provider: str):
    """Helper to run text processing logic with manual dependency injection."""
    async for db_session in get_db():
        if not isinstance(db_session, AsyncSession):
            raise TypeError("Expected db_session to be an AsyncSession")

        # --- Manual Dependency Injection for Celery Task ---
        event_bus = get_event_bus()
        storage_factory = get_storage_service_factory()
        media_repo = MediaRepository(db=db_session)
        media_queries = MediaQueries(media_repository=media_repo)

        # 1. Create the command handler
        handler = ProcessTextCommandHandler(
            media_queries=media_queries,
            media_repository=media_repo,
            storage_service_factory=storage_factory,
            event_bus=event_bus
        )

        # 2. Create the command
        command = ProcessTextCommand(
            media_id=media_id, 
            file_path=file_path,
            storage_provider=storage_provider
        )

        # 3. Execute the handler
        try:
            await handler.handle(command)
        except Exception as e:
            logger.error(f"Error processing text for media {media_id}: {str(e)}", exc_info=True)
            raise
