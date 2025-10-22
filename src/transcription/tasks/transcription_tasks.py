# src/transcription/tasks/transcription_tasks.py
import asyncio
import structlog
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional

from src.shared.infrastructure.database import get_db
from src.transcription.application.commands.commands import ProcessTranscriptionCommand
from src.transcription.application.commands.handlers import ProcessTranscriptionCommandHandler
from src.transcription.bootstrap import TranscriptionContainer

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_transcription_task(self, media_id: str, file_path: str, storage_provider: str, transcription_provider: str, language: str):
    """Celery entrypoint to trigger the transcription pipeline."""
    try:
        return asyncio.run(_run_transcription(media_id, file_path, storage_provider, transcription_provider, language))
    except Exception as e:
        logger.error(f"Error in transcription task for media {media_id}: {str(e)}", exc_info=True)
        return None


async def _run_transcription(media_id: str, file_path: str, storage_provider: str, transcription_provider: str, language: str):
    """Helper to run transcription logic with dependency injection."""
    async for db_session in get_db():
        if not isinstance(db_session, AsyncSession):
            raise TypeError("Expected db_session to be an AsyncSession")

        # --- Dependency Injection using Container ---
        transcription_container = TranscriptionContainer()
        transcription_container.db.override(db_session) # Sobrescrever a dependência do DB

        # 1. Create the command handler (resolved from container)
        handler: ProcessTranscriptionCommandHandler = transcription_container.process_transcription_command_handler()

        # 2. Create the command
        command = ProcessTranscriptionCommand(
            media_id=media_id,
            file_path=file_path,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            language=language
        )

        # 3. Execute the handler
        try:
            return await handler.handle(command)
        except Exception as e:
            logger.error(f"Error processing transcription for media {media_id}: {str(e)}", exc_info=True)
            raise
