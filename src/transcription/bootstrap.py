# src/transcription/bootstrap.py
from dataclasses import dataclass
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

# Concrete Implementations
from src.transcription.infrastructure.speech_recognizer import (
    WhisperSpeechRecognizer,
)
from src.transcription.infrastructure.transcription_repository import (
    TranscriptionRepository,
)
from src.transcription.infrastructure.logging import StructuredTranscriptionLogger
from src.transcription.infrastructure.metrics import PrometheusTranscriptionMetrics
from src.shared.infrastructure.storage.s3_storage_service import S3StorageService
from src.transcription.application.queries import TranscriptionQueries
from src.shared.events.event_bus import EventBus
from src.media_management.application.queries.media_queries import MediaQueries
from src.transcription.application.event_handlers import (
    register_event_handlers as register_transcription_handlers,
)

# Consolidated Service
from src.transcription.application.transcription_service import TranscriptionService


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

    # Consolidated Application Service
    transcription_service = providers.Factory(
        TranscriptionService,
        transcription_repo=transcription_repository,
        speech_recognizer=speech_recognizer,
        storage_service=storage_service,
        transcription_logger=transcription_logger,
        transcription_metrics=transcription_metrics
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
    event_bus: EventBus,
    media_queries: MediaQueries,
) -> TranscriptionModule:
    module = TranscriptionModule(
        service=container.transcription_service(),
        queries=container.transcription_queries(),
    )
    repository = container.transcription_repository()
    await register_transcription_handlers(
        event_bus,
        repository,
        media_queries,
    )
    return module


__all__ = [
    "TranscriptionContainer",
    "TranscriptionModule",
    "create_transcription_container",
    "build_transcription_module",
]
