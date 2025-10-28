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
    service: TranscriptionService
    repository: TranscriptionRepository
    queries: TranscriptionQueries


def build_transcription_module(session: AsyncSession) -> TranscriptionModule:
    container = TranscriptionContainer(db=session)
    return TranscriptionModule(
        service=container.transcription_service(),
        repository=container.transcription_repository(),
        queries=container.transcription_queries(),
    )
