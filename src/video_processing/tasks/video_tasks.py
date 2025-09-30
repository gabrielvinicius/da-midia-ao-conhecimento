# src/video_processing/tasks/video_tasks.py
import asyncio
import structlog
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.database import get_db
from src.shared.events.event_bus import get_event_bus
from src.storage.infrastructure.dependencies import get_storage_service_factory
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.infrastructure.media_repository import MediaRepository
from src.video_processing.application.commands.process_video_command import ProcessVideoCommand
from src.video_processing.application.commands.process_video_command_handler import ProcessVideoCommandHandler
from src.notifications.infrastructure.connection_manager import manager as connection_manager # Import manager

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_video_task(self, media_id: str, file_path: str):
    """Celery task to trigger the video processing (audio extraction) pipeline."""
    try:
        return asyncio.run(_run_video_processing(media_id, file_path))
    except Exception as e:
        logger.error(f"Error in video processing task for media {media_id}: {str(e)}", exc_info=True)
        return None


async def _run_video_processing(media_id: str, file_path: str):
    """Helper to run video processing logic with manual dependency injection."""
    async for db_session in get_db():
        if not isinstance(db_session, AsyncSession):
            raise TypeError("Expected db_session to be an AsyncSession")

        # --- Manual Dependency Injection for Celery Task ---
        event_bus = get_event_bus()
        storage_factory = get_storage_service_factory()
        media_repo = MediaRepository(db=db_session)
        media_queries = MediaQueries(media_repository=media_repo)

        # 1. Create the command handler with all dependencies
        handler = ProcessVideoCommandHandler(
            media_queries=media_queries,
            media_repository=media_repo, # Added dependency
            storage_service_factory=storage_factory,
            event_bus=event_bus,
            connection_manager=connection_manager # Added dependency
        )

        # 2. Create the command
        command = ProcessVideoCommand(media_id=media_id, file_path=file_path)

        # 3. Execute the handler
        try:
            await handler.handle(command)
        except Exception as e:
            logger.error(f"Error processing video for media {media_id}: {str(e)}", exc_info=True)
            raise
