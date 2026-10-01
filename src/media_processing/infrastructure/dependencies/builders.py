from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

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


def build_media_processing_event_handlers(
    *,
    session: AsyncSession,
    storage_factory: StorageServiceFactory,
    event_bus: SupportsEventBus,
    storage_provider: str,
) -> MediaProcessingEventHandlers:
    """Constrói o handler de MediaUploaded com dependências por evento."""

    transcription_repo = TranscriptionRepository(db=session)

    storage_service = storage_factory.create_storage_service(storage_provider)

    transcription_service = TranscriptionService(
        transcription_repo=transcription_repo,
        task_scheduler=CeleryTranscriptionTaskScheduler(),
        transcription_logger=StructuredTranscriptionLogger(),
        transcription_metrics=PrometheusTranscriptionMetrics(),
        storage_service=storage_service,
        speech_recognizer_factory=lambda provider: get_speech_recognizer(provider),
        event_bus=event_bus,
    )

    text_extraction_service = TextExtractionService(
        repository=transcription_repo,
        task_scheduler=CeleryTextTaskScheduler(),
        storage_service=storage_service,
        event_bus=event_bus,
        text_extractor=get_text_extractor(),
        ocr_provider=get_ocr_provider(),
    )

    return MediaProcessingEventHandlers(
        transcription_service=transcription_service,
        text_extraction_service=text_extraction_service,
    )


__all__ = ["build_media_processing_event_handlers"]
