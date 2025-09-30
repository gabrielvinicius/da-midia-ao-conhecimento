# src/transcription/tasks/tasks.py
import asyncio
import structlog
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from src.shared.events.event_bus import get_event_bus
from src.shared.infrastructure.database import get_db
from src.storage.infrastructure.dependencies import get_storage_service_factory
from src.transcription.application.commands.process_transcription_command import ProcessTranscriptionCommand
from src.transcription.application.commands.process_transcription_command_handler import ProcessTranscriptionCommandHandler
from src.transcription.application.commands.align_diarization_command import AlignDiarizationCommand
from src.transcription.application.commands.align_diarization_command_handler import AlignDiarizationCommandHandler
from src.transcription.application.services.alignment_service import AlignmentService
from src.transcription.infrastructure.dependencies import get_transcription_repository, create_speech_recognition_service
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.infrastructure.media_repository import MediaRepository
from src.metrics.application.metrics_service import MetricsService
from src.metrics.infrastructure.prometheus_provider import PrometheusMetricsProvider
from src.notifications.infrastructure.connection_manager import manager as connection_manager

logger = structlog.get_logger(__name__)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def process_transcription_task(
    self, 
    media_id: str, 
    file_path: str, 
    storage_provider: str, 
    transcription_provider: str, 
    language: str = "en"
):
    try:
        return asyncio.run(_run_transcription(media_id, file_path, storage_provider, transcription_provider, language))
    except Exception as e:
        logger.error(f"Error in transcription task for media {media_id}: {str(e)}", exc_info=True)
        return None


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, max_retries=3)
def align_diarization_task(self, media_id: str, diarization_result: List[Dict[str, Any]]):
    """Celery task to trigger the alignment of diarization and transcription."""
    try:
        return asyncio.run(_run_alignment(media_id, diarization_result))
    except Exception as e:
        logger.error(f"Error in alignment task for media {media_id}: {str(e)}", exc_info=True)
        return None


async def _run_transcription(media_id: str, file_path: str, storage_provider: str, transcription_provider: str, language: str):
    async for db_session in get_db():
        # ... (implementation remains the same)
        pass


async def _run_alignment(media_id: str, diarization_result: List[Dict[str, Any]]):
    """Helper to run alignment logic with manual dependency injection."""
    async for db_session in get_db():
        if not isinstance(db_session, AsyncSession):
            raise TypeError("Expected db_session to be an AsyncSession")

        # --- Manual Dependency Injection for Celery Task ---
        transcription_repo = await get_transcription_repository(db_session)
        media_repo = MediaRepository(db=db_session)
        media_queries = MediaQueries(media_repository=media_repo)
        alignment_service = AlignmentService()

        handler = AlignDiarizationCommandHandler(
            transcription_repository=transcription_repo,
            media_queries=media_queries,
            alignment_service=alignment_service,
            connection_manager=connection_manager
        )

        command = AlignDiarizationCommand(media_id=media_id, diarization_result=diarization_result)
        await handler.handle(command)


# The _run_transcription implementation needs to be brought back
async def _run_transcription(media_id: str, file_path: str, storage_provider: str, transcription_provider: str, language: str):
    async for db_session in get_db():
        event_bus = get_event_bus()
        metrics_service = MetricsService(provider=PrometheusMetricsProvider())
        storage_service_factory = get_storage_service_factory()
        media_repository = MediaRepository(db=db_session)
        media_queries = MediaQueries(media_repository=media_repository)
        storage_service = storage_service_factory(storage_provider)
        speech_recognition_service = create_speech_recognition_service(transcription_provider)
        transcription_repository = await get_transcription_repository(db_session)

        handler = ProcessTranscriptionCommandHandler(
            speech_recognition=speech_recognition_service,
            storage_service=storage_service,
            event_bus=event_bus,
            transcription_repository=transcription_repository,
            media_queries=media_queries,
            media_repository=media_repository,
            metrics_service=metrics_service,
            connection_manager=connection_manager
        )
        
        command = ProcessTranscriptionCommand(
            media_id=media_id, 
            file_path=file_path,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            language=language
        )
        await handler.handle(command)
