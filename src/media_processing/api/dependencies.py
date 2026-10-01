# src/transcription/api/dependencies.py
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)
from src.media_processing.infrastructure.adapters.celery_task_schedulers import (
    CeleryTranscriptionTaskScheduler,
)
from src.media_processing.infrastructure.dependencies.providers import (
    get_speech_recognizer,
)
from src.media_processing.infrastructure.logging import structured_transcription_logger
from src.media_processing.infrastructure.metrics import prometheus_transcription_metrics
from src.media_processing.infrastructure.repositories import transcription_repository
from src.media_management.infrastructure.repositories.media_repository import (
    MediaRepository,
)
from src.shared.infrastructure.database.db import get_db
from src.storage.infrastructure.dependencies import StorageServiceFactory


class TranscriptionDependenciesNotConfiguredError(RuntimeError):
    pass


@dataclass(frozen=True)
class TranscriptionDependencies:
    service: TranscriptionService


def _get_event_bus(request: Request):
    bus = getattr(request.app.state, "event_bus", None)
    return bus


def get_transcription_dependencies(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TranscriptionDependencies:
    """Provider padrão (por request) para o serviço de transcrição."""

    TranscriptionRepository = transcription_repository.TranscriptionRepository
    StructuredTranscriptionLogger = (
        structured_transcription_logger.StructuredTranscriptionLogger
    )
    PrometheusTranscriptionMetrics = (
        prometheus_transcription_metrics.PrometheusTranscriptionMetrics
    )

    repo = TranscriptionRepository(db=session)
    storage_factory = StorageServiceFactory()
    storage_service = storage_factory.create_storage_service("local")
    media_queries = MediaRepository(db=session)
    event_bus = _get_event_bus(request)

    service = TranscriptionService(
        transcription_repo=repo,
        task_scheduler=CeleryTranscriptionTaskScheduler(),
        transcription_logger=StructuredTranscriptionLogger(),
        transcription_metrics=PrometheusTranscriptionMetrics(),
        storage_service=storage_service,
        speech_recognizer_factory=lambda provider: get_speech_recognizer(provider),
        media_queries=media_queries,
        event_bus=event_bus,
    )

    return TranscriptionDependencies(service=service)


TranscriptionDeps = Annotated[
    TranscriptionDependencies, Depends(get_transcription_dependencies)
]


def get_transcription_service(deps: TranscriptionDeps) -> TranscriptionService:
    """Get transcription service dependency."""
    return deps.service


__all__ = [
    "TranscriptionDependencies",
    "TranscriptionDependenciesNotConfiguredError",
    "get_transcription_dependencies",
    "get_transcription_service",
]
