# src/summarization/tasks/summary_tasks.py
import asyncio
import structlog
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from src.shared.infrastructure.database import get_db

from src.summarization.application.commands.commands import ProcessSummaryCommand
from src.summarization.application.commands.handlers import ProcessSummaryCommandHandler
from src.summarization.bootstrap import SummarizationContainer

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_summary_task(self, media_id: str, text_content: str, provider: str):
    """Celery entrypoint to trigger the summarization pipeline from any text source."""
    try:
        return asyncio.run(_run_summarization(media_id, text_content, provider))
    except Exception as e:
        logger.error(f"Error in summarization task for media {media_id}: {str(e)}", exc_info=True)
        return None


async def _run_summarization(media_id: str, text_content: str, provider: str):
    """Helper to run summarization logic with dependency injection."""
    async for db_session in get_db():
        if not isinstance(db_session, AsyncSession):
            raise TypeError("Expected db_session to be an AsyncSession")

        # --- Dependency Injection using Container ---
        summarization_container = SummarizationContainer()
        summarization_container.db.override(db_session) # Sobrescrever a dependência do DB

        # 1. Create the command handler (resolved from container)
        handler: ProcessSummaryCommandHandler = summarization_container.process_summary_command_handler()

        # 2. Create the command
        command = ProcessSummaryCommand(
            media_id=media_id,
            text_content=text_content,
            provider=provider
        )

        # 3. Execute the handler
        try:
            return await handler.handle(command)
        except Exception as e:
            logger.error(f"Error processing summarization for media {media_id}: {str(e)}", exc_info=True)
            raise