"""Helpers to compose media_processing services for worker processes.

Mantém a construção de dependências em um único ponto, evitando duplicação
nas tasks e permitindo troca de adapters/metrics via providers.
"""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from src.media_processing.application.services.text_extraction_service import (
    TextExtractionService,
)
from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)
from src.media_processing.application.services.video_processing_service import (
    VideoProcessingService,
)
from src.media_processing.infrastructure.adapters.storage_download_adapter import (
    StorageDownloadAdapter,
)
from src.media_processing.infrastructure.dependencies.providers import (
    get_audio_extractor,
    get_ocr_provider,
    get_speech_recognizer,
    get_text_extractor,
    get_thumbnail_generator,
)
from src.media_processing.infrastructure.logging import (
    structured_transcription_logger,
)
from src.media_processing.infrastructure.metrics import (
    prometheus_transcription_metrics,
    prometheus_video_processing_metrics,
)
from src.media_processing.infrastructure.repositories import (
    transcription_repository,
)
from src.shared.infrastructure.messaging.event_bus import SupportsEventBus
from src.storage.infrastructure.dependencies import StorageServiceFactory

StructuredTranscriptionLogger = (
    structured_transcription_logger.StructuredTranscriptionLogger
)
PrometheusTranscriptionMetrics = (
    prometheus_transcription_metrics.PrometheusTranscriptionMetrics
)
PrometheusVideoProcessingMetrics = (
    prometheus_video_processing_metrics.PrometheusVideoProcessingMetrics
)
TranscriptionRepository = transcription_repository.TranscriptionRepository


def build_transcription_service(
    session,
    event_bus: SupportsEventBus,
    storage_provider: str = "local",
) -> TranscriptionService:
    repo = TranscriptionRepository(session)
    metrics = PrometheusTranscriptionMetrics()
    transcription_logger = StructuredTranscriptionLogger()
    storage = StorageServiceFactory().create_storage_service(storage_provider)
    return TranscriptionService(
        transcription_repo=repo,
        task_scheduler=None,  # Worker executa direto, sem agendar
        transcription_logger=transcription_logger,
        transcription_metrics=metrics,
        storage_service=storage,
        speech_recognizer_factory=lambda provider: get_speech_recognizer(provider),
        media_queries=None,
        event_bus=event_bus,
        stats_recorder=_stats_recorder(session),
    )


def _stats_recorder(session):
    """Repositório de durações; ausente quando não há sessão (ex.: testes)."""
    if session is None:
        return None
    from src.shared.infrastructure.repositories.processing_stats_repository import (
        ProcessingStatsRepository,
    )

    return ProcessingStatsRepository(session)


def build_text_extraction_service(
    session,
    event_bus: SupportsEventBus,
    storage_provider: str = "local",
) -> TextExtractionService:
    repo = TranscriptionRepository(session)
    metrics = PrometheusTranscriptionMetrics()
    logger = StructuredTranscriptionLogger()
    storage = StorageServiceFactory().create_storage_service(storage_provider)

    return TextExtractionService(
        repository=repo,
        task_scheduler=None,  # Worker executa direto
        storage_service=storage,
        text_extractor=get_text_extractor(),
        ocr_provider=get_ocr_provider(),
        event_bus=event_bus,
        metrics=metrics,
        logger=logger,
    )


def build_video_processing_service(
    session,
    event_bus: SupportsEventBus,
    storage_provider: str = "local",
) -> VideoProcessingService:
    metrics = PrometheusVideoProcessingMetrics()
    storage_factory = StorageServiceFactory()
    storage_adapter = StorageDownloadAdapter(storage_factory)

    return VideoProcessingService(
        video_audio_extractor=get_audio_extractor(),
        video_thumbnail_generator=get_thumbnail_generator(),
        video_processing_task_scheduler=None,  # executado inline no worker
        storage_factory=storage_adapter,
        event_bus=event_bus,
        video_processing_metrics=metrics,
    )


class MediaProcessingServices:
    """Convenience container para tasks."""

    def __init__(
        self,
        transcription: TranscriptionService,
        text_extraction: TextExtractionService,
        video_processing: VideoProcessingService,
    ) -> None:
        self.transcription = transcription
        self.text_extraction = text_extraction
        self.video_processing = video_processing


def build_services(
    session,
    event_bus: SupportsEventBus,
    storage_provider: str = "local",
) -> MediaProcessingServices:
    return MediaProcessingServices(
        transcription=build_transcription_service(
            session, event_bus, storage_provider
        ),
        text_extraction=build_text_extraction_service(
            session, event_bus, storage_provider
        ),
        video_processing=build_video_processing_service(
            session, event_bus, storage_provider
        ),
    )


__all__ = [
    "build_services",
    "build_transcription_service",
    "build_text_extraction_service",
    "build_video_processing_service",
    "MediaProcessingServices",
]
