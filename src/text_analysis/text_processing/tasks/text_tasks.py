# src/text_processing/tasks/text_tasks.py
from typing import Any, Dict, Optional

import structlog
from celery import shared_task
from pydantic import ValidationError

from src.shared.infrastructure.database import get_sync_db
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
        # Use synchronous database session in Celery worker
        with get_sync_db() as db_session:
            return _run_text_processing_sync(payload, db_session)
    except Exception as e:
        logger.error(f"Error in text processing task for media {media_id}: {str(e)}", exc_info=True)
        return None


def _run_text_processing_sync(payload: TextProcessPayload, db_session):
    """Synchronous helper to run text processing logic with dependency injection."""
    # --- Dependency Injection using Container ---
    text_processing_container = TextProcessingContainer()
    text_processing_container.db.override(db_session)  # Override the DB dependency
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

    # 3. Execute the handler - use sync version if available
    try:
        # Check if the handler has a sync method, otherwise use async in new event loop
        if hasattr(handler, 'handle_sync'):
            return handler.handle_sync(command)
        else:
            # Fallback: run async method in a new event loop
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
            "text_processing.task_legacy_failed",
            media_id=str(payload.media_id),
            error=str(e),
            exc_info=True,
        )
        raise
