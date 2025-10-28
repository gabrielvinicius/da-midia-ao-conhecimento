# src/transcription/bootstrap.py
from dataclasses import dataclass
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

# Concrete Implementations
from src.transcription.infrastructure.speech_recognizer import WhisperSpeechRecognizer
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository
from src.transcription.infrastructure.logging import StructuredTranscriptionLogger
from src.transcription.infrastructure.metrics import PrometheusTranscriptionMetrics
from src.shared.infrastructure.storage.s3_storage_service import S3StorageService
from src.transcription.application.queries import TranscriptionQueries

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


@dataclass
class TranscriptionEventContext:
    """Dependencies required for registering transcription event handlers."""

    repository: TranscriptionRepository


def create_transcription_container(session: AsyncSession) -> TranscriptionContainer:
    """Configure the transcription container for the given session."""

    return TranscriptionContainer(db=session)


def build_transcription_module(
    container: TranscriptionContainer,
) -> TranscriptionModule:
    return TranscriptionModule(
        service=container.transcription_service(),
        queries=container.transcription_queries(),
    )


def build_transcription_event_context(
    container: TranscriptionContainer,
) -> TranscriptionEventContext:
    return TranscriptionEventContext(
        repository=container.transcription_repository(),
    )


__all__ = [
    "TranscriptionContainer",
    "TranscriptionModule",
    "TranscriptionEventContext",
    "create_transcription_container",
    "build_transcription_module",
    "build_transcription_event_context",
]
