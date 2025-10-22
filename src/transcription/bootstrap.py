# src/transcription/bootstrap.py
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.transcription.domain.interfaces import (
    ISpeechRecognizer,
    ITranscriptionRepository,
    ITranscriptionTaskScheduler,
    TranscriptionOperationLogger,
    TranscriptionMetrics
)
from src.transcription.infrastructure.speech_recognizer import WhisperSpeechRecognizer
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository
from src.transcription.infrastructure.task_scheduler import CeleryTranscriptionTaskScheduler
from src.transcription.infrastructure.logging import StructuredTranscriptionLogger
from src.transcription.infrastructure.metrics import PrometheusTranscriptionMetrics
from src.transcription.application.commands.handlers import ProcessTranscriptionCommandHandler, SetSpeakerAliasesCommandHandler
from src.transcription.application.transcription_service import TranscriptionService
from src.shared.infrastructure.storage.s3_storage_service import S3StorageService

class TranscriptionContainer(containers.DeclarativeContainer):
    # Dependências de infraestrutura
    db: providers.Provider[AsyncSession] = providers.Dependency()
    storage_service: providers.Provider[S3StorageService] = providers.Singleton(S3StorageService)

    # Implementações concretas das interfaces de domínio
    speech_recognizer: providers.Provider[ISpeechRecognizer] = providers.Factory(
        WhisperSpeechRecognizer
    )
    transcription_repository: providers.Provider[ITranscriptionRepository] = providers.Factory(
        TranscriptionRepository,
        db=db
    )
    transcription_task_scheduler: providers.Provider[ITranscriptionTaskScheduler] = providers.Factory(
        CeleryTranscriptionTaskScheduler
    )
    transcription_logger: providers.Provider[TranscriptionOperationLogger] = providers.Singleton(
        StructuredTranscriptionLogger
    )
    transcription_metrics: providers.Provider[TranscriptionMetrics] = providers.Singleton(
        PrometheusTranscriptionMetrics
    )

    # Serviços de Aplicação
    transcription_service: providers.Provider[TranscriptionService] = providers.Factory(
        TranscriptionService,
        transcription_repo=transcription_repository,
        task_scheduler=transcription_task_scheduler,
        transcription_logger=transcription_logger,
        transcription_metrics=transcription_metrics
    )

    # Command Handlers
    process_transcription_command_handler: providers.Provider[ProcessTranscriptionCommandHandler] = providers.Factory(
        ProcessTranscriptionCommandHandler,
        transcription_repo=transcription_repository,
        speech_recognizer=speech_recognizer,
        storage_service=storage_service,
        transcription_logger=transcription_logger,
        transcription_metrics=transcription_metrics
    )
    set_speaker_aliases_command_handler: providers.Provider[SetSpeakerAliasesCommandHandler] = providers.Factory(
        SetSpeakerAliasesCommandHandler,
        transcription_repo=transcription_repository,
        transcription_logger=transcription_logger,
        transcription_metrics=transcription_metrics
    )
