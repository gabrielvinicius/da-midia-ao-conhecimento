# src/transcription/bootstrap.py
from dataclasses import dataclass

from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.application.queries.media_queries import MediaQueries
from src.shared.infrastructure.storage.s3_storage_service import S3StorageService
from src.transcription.application.queries import TranscriptionQueries
# Consolidated Service
from src.transcription.application.transcription_service import TranscriptionService
from src.transcription.infrastructure.logging import StructuredTranscriptionLogger
from src.transcription.infrastructure.metrics import PrometheusTranscriptionMetrics
# Concrete Implementations
from src.transcription.infrastructure.speech_recognizer import (
    WhisperSpeechRecognizer,
)
from src.transcription.infrastructure.task_scheduler import CeleryTranscriptionTaskScheduler
from src.transcription.infrastructure.transcription_repository import (
    TranscriptionRepository,
)


class TranscriptionContainer(containers.DeclarativeContainer):
    db: providers.Provider[AsyncSession] = providers.Dependency()

    # Infrastructure Services
    storage_service = providers.Singleton(S3StorageService)
    speech_recognizer = providers.Factory(WhisperSpeechRecognizer)
    transcription_repository = providers.Factory(TranscriptionRepository, db=db)
    transcription_queries = providers.Factory(
        TranscriptionQueries,
        transcription_repository=transcription_repository,
    )
    transcription_logger = providers.Singleton(StructuredTranscriptionLogger)
    transcription_metrics = providers.Singleton(PrometheusTranscriptionMetrics)
    task_scheduler = providers.Factory(CeleryTranscriptionTaskScheduler)

    # Consolidated Application Service
    transcription_service = providers.Factory(
        TranscriptionService,
        transcription_repo=transcription_repository,
        task_scheduler=task_scheduler,
        transcription_logger=transcription_logger,
        transcription_metrics=transcription_metrics,
    )


@dataclass
class TranscriptionModule:
    """Surface exposed to the transcription API."""

    service: TranscriptionService
    queries: TranscriptionQueries


def create_transcription_container(session: AsyncSession) -> TranscriptionContainer:
    """Configure the transcription container for the given session."""

    return TranscriptionContainer(db=session)


async def build_transcription_module(
    container: TranscriptionContainer,
    *,
    media_queries: MediaQueries,
) -> TranscriptionModule:
    module = TranscriptionModule(
        service=container.transcription_service(),
        queries=container.transcription_queries(),
    )
    # Skip EventBus handler registration; pipeline runs via Celery tasks
    return module


__all__ = [
    "TranscriptionContainer",
    "TranscriptionModule",
    "create_transcription_container",
    "build_transcription_module",
]
