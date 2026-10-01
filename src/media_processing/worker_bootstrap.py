"""Helpers to compose media_processing services for worker processes.

Mantém a construção de dependências em um único ponto, evitando duplicação
nas tasks e permitindo troca de adapters/metrics via providers.
"""
from __future__ import annotations

from src.media_processing.application.services.text_extraction_service import (
    TextExtractionService,
)
from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)
from src.media_processing.infrastructure.dependencies.providers import (
    get_ocr_provider,
    get_speech_recognizer,
    get_text_extractor,
)
from src.media_processing.infrastructure.adapters.video.ffprobe_duration_probe import (
    FfprobeDurationProbe,
)
from src.media_processing.infrastructure.logging import (
    structured_transcription_logger,
)
from src.media_processing.infrastructure.metrics import (
    prometheus_transcription_metrics,
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
        duration_probe=FfprobeDurationProbe(),
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


def build_stalled_processing_monitor(session, event_bus: SupportsEventBus):
    from src.media_processing.application.services.stalled_processing_monitor import (
        StalledProcessingMonitor,
    )
    from src.media_processing.config.settings import processing_settings
    from src.media_processing.infrastructure.adapters.celery_task_terminator import (
        CeleryTaskTerminator,
    )

    return StalledProcessingMonitor(
        repository=TranscriptionRepository(session),
        transcription_service=build_transcription_service(session, event_bus),
        policy=processing_settings.deadline_policy(),
        realtime_factors=_stats_recorder(session),
        terminator=CeleryTaskTerminator(),
    )


def build_unstarted_media_recovery(session, event_bus: SupportsEventBus):
    from src.media_processing.application.services.unstarted_media_recovery import (
        UnstartedMediaRecovery,
    )
    from src.media_processing.config.settings import processing_settings
    from src.media_processing.infrastructure.adapters.unstarted_media_query import (
        SqlUnstartedMediaQuery,
    )
    from src.media_processing.infrastructure.dependencies.builders import (
        build_media_processing_event_handlers,
    )

    return UnstartedMediaRecovery(
        query=SqlUnstartedMediaQuery(session),
        # O mesmo tratamento do envio: cria o registro e agenda a tarefa.
        upload_handler=build_media_processing_event_handlers(
            session=session,
            storage_factory=StorageServiceFactory(),
            event_bus=event_bus,
            storage_provider="local",
        ),
        event_bus=event_bus,
        grace_seconds=processing_settings.unstarted_grace_minutes * 60,
        give_up_seconds=processing_settings.unstarted_give_up_minutes * 60,
    )


class MediaProcessingServices:
    """Convenience container para tasks."""

    def __init__(
        self,
        transcription: TranscriptionService,
        text_extraction: TextExtractionService,
    ) -> None:
        self.transcription = transcription
        self.text_extraction = text_extraction


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
    )


__all__ = [
    "build_services",
    "build_transcription_service",
    "build_text_extraction_service",
    "build_stalled_processing_monitor",
    "build_unstarted_media_recovery",
    "MediaProcessingServices",
]
