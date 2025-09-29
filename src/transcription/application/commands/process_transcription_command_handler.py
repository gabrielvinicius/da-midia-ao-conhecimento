# src/transcription/application/commands/process_transcription_command_handler.py
import time
import structlog

from src.metrics.application.metrics_service import MetricsService
from src.shared.events.domain_events import TextContentReady, TranscriptionFailed, TranscriptionStarted
from src.shared.events.event_bus import EventBus
from src.storage.application.storage_service import StorageService
from src.transcription.domain.transcription import Transcription, TranscriptionStatus
from src.transcription.infrastructure.interfaces import ISpeechRecognition
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.infrastructure.media_repository import MediaRepository
from .process_transcription_command import ProcessTranscriptionCommand
from src.shared.resilience.circuit_breaker import get_circuit_breaker

logger = structlog.get_logger(__name__)


class ProcessTranscriptionCommandHandler:
    def __init__(
        self,
        speech_recognition: ISpeechRecognition,
        storage_service: StorageService,
        event_bus: EventBus,
        transcription_repository: TranscriptionRepository,
        media_queries: MediaQueries,
        media_repository: MediaRepository,
        metrics_service: MetricsService,
    ):
        self.speech_recognition = speech_recognition
        self.storage_service = storage_service
        self.event_bus = event_bus
        self.transcription_repo = transcription_repository
        self.media_queries = media_queries
        self.media_repository = media_repository
        self.metrics_service = metrics_service

    async def handle(self, command: ProcessTranscriptionCommand) -> Transcription:
        start_time = time.time()
        logger.info("transcription.started", media_id=command.media_id, provider=command.transcription_provider)

        media = await self.media_queries.get_by_id(command.media_id)
        if not media:
            raise ValueError(f"Media with id {command.media_id} not found.")

        transcription = await self.transcription_repo.find_by_media_id(command.media_id)

        try:
            media.process()
            await self.media_repository.save(media)
            await self.event_bus.publish(TranscriptionStarted(media_id=command.media_id))

            if transcription and transcription.text and transcription.status == TranscriptionStatus.COMPLETED:
                media.complete()
                await self.media_repository.save(media)
                logger.info("transcription.completed", media_id=command.media_id, from_cache=True)
                await self.event_bus.publish(TextContentReady(media_id=str(media.id), text_content=transcription.text))
                return transcription

            if transcription is None:
                transcription = Transcription(media_id=command.media_id, status=TranscriptionStatus.PROCESSING, provider=command.transcription_provider)
            else:
                transcription.provider = command.transcription_provider
            
            await self.transcription_repo.save(transcription)

            audio_bytes, _ = await self.storage_service.download(command.file_path)

            breaker_key = f"transcription_{self.speech_recognition.provider_name}"
            breaker = get_circuit_breaker(breaker_key)
            text = await breaker.call_async(self.speech_recognition.transcribe, audio_bytes, language=command.language)

            transcription.mark_as_completed(text)
            await self.transcription_repo.save(transcription)
            
            media.complete()
            await self.media_repository.save(media)

            await self.event_bus.publish(TextContentReady(media_id=command.media_id, text_content=text))

            duration = time.time() - start_time
            self.metrics_service.increment_transcription('success')
            self.metrics_service.observe_transcription_duration(
                media_id=command.media_id, # Corrected parameter name
                duration=duration, 
                provider=self.speech_recognition.provider_name
            )

            logger.info("transcription.completed", media_id=command.media_id, duration=duration)
            return transcription

        except Exception as e:
            duration = time.time() - start_time
            self.metrics_service.increment_transcription('failure')
            logger.error("transcription.failed", media_id=command.media_id, error=str(e), duration=duration)

            if media:
                media.fail(str(e)[:500])
                await self.media_repository.save(media)

            if transcription:
                transcription.mark_as_failed(str(e)[:500])
                await self.transcription_repo.save(transcription)

            await self.event_bus.publish(TranscriptionFailed(media_id=command.media_id, error=str(e)))
            raise
