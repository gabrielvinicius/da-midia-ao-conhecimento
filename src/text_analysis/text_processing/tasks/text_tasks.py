# src/text_processing/tasks/text_tasks.py
import asyncio
from typing import Any, Dict, Optional

import structlog
from celery import shared_task
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.database import get_db
from src.text_analysis.application.schemas import TextProcessPayload
from src.text_analysis.text_processing.application.commands.commands import (
    ProcessTextCommand,
)
from src.text_analysis.text_processing.application.commands.handlers import (
    ProcessTextCommandHandler,
)
from src.text_analysis.text_processing.bootstrap import TextProcessingContainer
from src.storage.infrastructure.dependencies import StorageServiceFactory

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def process_text_task(self, media_id: str, text_content: str, processing_type: str, options: Optional[Dict[str, Any]] = None):
    """Celery task to trigger the text processing pipeline."""
    try:
        payload = TextProcessPayload.model_validate(
            {
                "media_id": media_id,
                "text_content": text_content,
                "processing_type": processing_type,
                "options": options,
            }
        )
    except ValidationError as exc:
        logger.error(
            "text_processing.task_invalid_payload_legacy",
            media_id=media_id,
            errors=exc.errors(),
        )
        return None

    try:
        return asyncio.run(_run_text_processing(payload))
    except Exception as e:
        logger.error(f"Error in text processing task for media {media_id}: {str(e)}", exc_info=True)
        return None


async def _run_text_processing(payload: TextProcessPayload):
    """Helper to run text processing logic with dependency injection."""
    async for db_session in get_db():
        if not isinstance(db_session, AsyncSession):
            raise TypeError("Expected db_session to be an AsyncSession")

        # --- Dependency Injection using Container ---
        text_processing_container = TextProcessingContainer()
        text_processing_container.db.override(db_session)  # Sobrescrever a dependência do DB
        text_processing_container.storage_factory.override(StorageServiceFactory())

        # 1. Create the command handler (resolved from container)
        handler: ProcessTextCommandHandler = text_processing_container.process_text_command_handler()

        # 2. Create the command
        command = ProcessTextCommand(
            media_id=str(payload.media_id),
            text_content=payload.text_content,
            processing_type=payload.processing_type,
            options=payload.options,
        )

        # 3. Execute the handler
        try:
            await handler.handle(command)
        except Exception as e:
            logger.error(
                "text_processing.task_legacy_failed",
                media_id=str(payload.media_id),
                error=str(e),
                exc_info=True,
            )
            raise
