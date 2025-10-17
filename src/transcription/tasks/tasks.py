# src/transcription/tasks/tasks.py
import asyncio
import structlog
from celery import shared_task
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any

from src.shared.events.event_bus import get_event_bus
from src.shared.infrastructure.database import get_db
from src.storage.infrastructure.dependencies import get_storage_service_factory
from src.transcription.application.commands.commands import ProcessTranscriptionCommand
from src.transcription.application.commands.handlers import ProcessTranscriptionCommandHandler
# Diarization removed
# from src.transcription.application.commands.align_diarization_command import AlignDiarizationCommand
# from src.transcription.application.commands.align_diarization_command_handler import AlignDiarizationCommandHandler
from src.transcription.application.services.alignment_service import AlignmentService
from src.transcription.application.services.transcription_state_service import TranscriptionStateService
from src.transcription.application.services.transcription_file_service import TranscriptionFileService
from src.transcription.application.services.speech_recognition_service import SpeechRecognitionService
from src.transcription.application.services.transcription_event_service import TranscriptionEventService
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


# Diarization alignment task removed


async def _run_transcription(media_id: str, file_path: str, storage_provider: str, transcription_provider: str, language: str):
    async for db_session in get_db():
        # ... (implementation remains the same)
        pass


# Diarization alignment function removed


# The _run_transcription implementation needs to be brought back
async def _run_transcription(media_id: str, file_path: str, storage_provider: str, transcription_provider: str, language: str):
    async for db_session in get_db():
        # --- Dependency Instantiation ---
        event_bus = get_event_bus()
        metrics_service = MetricsService(provider=PrometheusMetricsProvider())
        storage_service_factory = get_storage_service_factory()
        storage_service = storage_service_factory.create_storage_service(storage_provider)
        
        media_repository = MediaRepository(db=db_session)
        media_queries = MediaQueries(media_repository=media_repository)
        transcription_repository = await get_transcription_repository(db_session)
        
        # Instantiate the specific speech recognition provider
        speech_recognition_provider = create_speech_recognition_service(transcription_provider)

        # --- Instantiate New SRP Services ---
        state_service = TranscriptionStateService(media_repository, transcription_repository)
        file_service = TranscriptionFileService(storage_service)
        recognition_service = SpeechRecognitionService(speech_recognition_provider)
        event_service = TranscriptionEventService(event_bus)

        # --- Instantiate the Orchestrator (Command Handler) ---
        handler = ProcessTranscriptionCommandHandler(
            media_queries=media_queries,
            state_service=state_service,
            file_service=file_service,
            recognition_service=recognition_service,
            event_service=event_service,
            metrics_service=metrics_service,
        )
        
        command = ProcessTranscriptionCommand(
            media_id=media_id, 
            file_path=file_path,
            storage_provider=storage_provider,
            transcription_provider=transcription_provider,
            language=language
        )
        await handler.handle(command)
