"""Montagem dos serviços do processamento: um único lugar para a API e os workers.

Antes, o mesmo serviço era montado em quatro lugares com dependências
diferentes (a API, o worker, os handlers e até o módulo de mídias); a
estimativa de tempo, por exemplo, só funcionava na montagem que recebia o
repositório de durações.
"""
from __future__ import annotations

from typing import Optional

import structlog

from src.media_processing.application.event_handlers import MediaProcessingEventHandlers
from src.media_processing.application.services.text_extraction_service import (
    TextExtractionService,
)
from src.media_processing.application.services.transcription_service import (
    TranscriptionService,
)
from src.media_processing.infrastructure.adapters.celery_task_schedulers import (
    CeleryTextTaskScheduler,
    CeleryTranscriptionTaskScheduler,
)
from src.media_processing.infrastructure.adapters.video.ffprobe_duration_probe import (
    FfprobeDurationProbe,
)
from src.media_processing.infrastructure.dependencies.providers import (
    get_ocr_provider,
    get_speech_recognizer,
    get_text_extractor,
)
from src.media_processing.infrastructure.logging.structured_transcription_logger import (
    StructuredTranscriptionLogger,
)
from src.media_processing.infrastructure.metrics.prometheus_transcription_metrics import (
    PrometheusTranscriptionMetrics,
)
from src.media_processing.infrastructure.repositories.transcription_repository import (
    TranscriptionRepository,
)
from src.shared.application.event_bus import SupportsEventBus
from src.storage.infrastructure.dependencies import StorageServiceFactory

logger = structlog.get_logger(__name__)


def _stats_recorder(session):
    """Repositório de durações; ausente quando não há sessão (ex.: testes)."""
    if session is None:
        return None
    from src.shared.infrastructure.repositories.processing_stats_repository import (
        ProcessingStatsRepository,
    )

    return ProcessingStatsRepository(session)


def _visual_describer(stats=None):
    """Descrição de quadros dos vídeos; o modelo só é carregado ao ser usado."""
    from src.media_processing.application.services.visual_description_service import (
        VisualDescriptionService,
    )
    from src.media_processing.infrastructure.adapters.video.ffmpeg_frame_extractor import (
        FFmpegFrameExtractor,
    )
    from src.media_processing.infrastructure.dependencies.providers import get_visual_analyzer
    from src.shared.infrastructure.config.settings import settings

    if settings.visual_provider.strip().lower() == "none":
        return None  # VISUAL_PROVIDER=none: os vídeos seguem só com a fala
    try:
        analyzer = get_visual_analyzer(settings.visual_provider)
    except Exception as exc:  # sem provedor de visão, os vídeos seguem só com a fala
        logger.warning("visual_description.unavailable", error=str(exc))
        return None
    return VisualDescriptionService(analyzer, FFmpegFrameExtractor(), stats=stats)


def build_transcription_service(
    session,
    event_bus: Optional[SupportsEventBus],
    storage_provider: str = "local",
    storage_factory: Optional[StorageServiceFactory] = None,
) -> TranscriptionService:
    """Agenda (API e handlers) e executa (worker) transcrições; estima o tempo."""
    stats = _stats_recorder(session)
    storage_factory = storage_factory or StorageServiceFactory()
    return TranscriptionService(
        transcription_repo=TranscriptionRepository(session),
        task_scheduler=CeleryTranscriptionTaskScheduler(),
        transcription_logger=StructuredTranscriptionLogger(),
        transcription_metrics=PrometheusTranscriptionMetrics(),
        storage_service=storage_factory.create_storage_service(storage_provider),
        speech_recognizer_factory=lambda provider: get_speech_recognizer(provider),
        event_bus=event_bus,
        stats_recorder=stats,
        duration_probe=FfprobeDurationProbe(),
        visual_describer=_visual_describer(stats),
    )


def build_text_extraction_service(
    session,
    event_bus: Optional[SupportsEventBus],
    storage_provider: str = "local",
    storage_factory: Optional[StorageServiceFactory] = None,
) -> TextExtractionService:
    storage_factory = storage_factory or StorageServiceFactory()
    return TextExtractionService(
        repository=TranscriptionRepository(session),
        task_scheduler=CeleryTextTaskScheduler(),
        storage_service=storage_factory.create_storage_service(storage_provider),
        text_extractor=get_text_extractor(),
        ocr_provider=get_ocr_provider(),
        event_bus=event_bus,
        metrics=PrometheusTranscriptionMetrics(),
        logger=StructuredTranscriptionLogger(),
    )


def build_media_processing_event_handlers(
    *,
    session,
    storage_factory: StorageServiceFactory,
    event_bus: SupportsEventBus,
    storage_provider: str,
) -> MediaProcessingEventHandlers:
    """Handler de MediaUploaded: cria o registro e agenda a tarefa."""
    return MediaProcessingEventHandlers(
        transcription_service=build_transcription_service(
            session, event_bus, storage_provider, storage_factory
        ),
        text_extraction_service=build_text_extraction_service(
            session, event_bus, storage_provider, storage_factory
        ),
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


__all__ = [
    "build_media_processing_event_handlers",
    "build_stalled_processing_monitor",
    "build_text_extraction_service",
    "build_transcription_service",
]
