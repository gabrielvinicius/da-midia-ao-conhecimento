# src/text_processing/tasks/text_tasks.py
import asyncio
import structlog
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from src.shared.infrastructure.database import get_db
from src.text_processing.application.commands.commands import ProcessTextCommand
from src.text_processing.application.commands.handlers import ProcessTextCommandHandler

from src.text_processing.bootstrap import TextProcessingContainer

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_text_task(self, media_id: str, text_content: str, processing_type: str, options: Optional[Dict[str, Any]] = None):
    """Celery task to trigger the text processing pipeline."""
    try:
        return asyncio.run(_run_text_processing(media_id, text_content, processing_type, options))
    except Exception as e:
        logger.error(f"Error in text processing task for media {media_id}: {str(e)}", exc_info=True)
        return None


async def _run_text_processing(media_id: str, text_content: str, processing_type: str, options: Optional[Dict[str, Any]] = None):
    """Helper to run text processing logic with dependency injection."""
    async for db_session in get_db():
        if not isinstance(db_session, AsyncSession):
            raise TypeError("Expected db_session to be an AsyncSession")

        # --- Dependency Injection using Container ---
        text_processing_container = TextProcessingContainer()
        text_processing_container.db.override(db_session) # Sobrescrever a dependência do DB

        # 1. Create the command handler (resolved from container)
        handler: ProcessTextCommandHandler = text_processing_container.process_text_command_handler()

        # 2. Create the command
        command = ProcessTextCommand(
            media_id=media_id,
            text_content=text_content,
            processing_type=processing_type,
            options=options
        )

        # 3. Execute the handler
        try:
            await handler.handle(command)
        except Exception as e:
            logger.error(f"Error processing text for media {media_id}: {str(e)}", exc_info=True)
            raise
