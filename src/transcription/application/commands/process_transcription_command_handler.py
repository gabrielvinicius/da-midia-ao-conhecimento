# src/transcription/application/commands/process_transcription_command_handler.py
import time
import json
import structlog
from pydantic import BaseModel

from src.metrics.application.metrics_service import MetricsService
from src.shared.events.domain_events import TextContentReady, TranscriptionFailed, TranscriptionWithTimestampsReady
from src.shared.events.event_bus import EventBus
from src.storage.application.storage_service import StorageService
from src.transcription.domain.transcription import Transcription
from src.transcription.infrastructure.interfaces import ISpeechRecognition
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.infrastructure.media_repository import MediaRepository
from src.notifications.infrastructure.connection_manager import ConnectionManager
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
        connection_manager: ConnectionManager,
    ):
        self.speech_recognition = speech_recognition
        self.storage_service = storage_service
        self.event_bus = event_bus
        self.transcription_repo = transcription_repository
        self.media_queries = media_queries
        self.media_repository = media_repository
        self.metrics_service = metrics_service
        self.connection_manager = connection_manager

    async def _push_update(self, entity_name: str, entity: BaseModel, user_id: str):
        message = {
            "type": "entity_update",
            "entity": entity_name,
            "payload": json.loads(entity.model_dump_json())
        }
        await self.connection_manager.send_personal_message(json.dumps(message), user_id)
        logger.info(f"{entity_name}.pushed_realtime_update", id=str(entity.id), user_id=user_id)

    async def handle(self, command: ProcessTranscriptionCommand) -> Transcription:
        start_time = time.time()
        logger.info("transcription.started", media_id=command.media_id, provider=command.transcription_provider)

        media = await self.media_queries.get_by_id(command.media_id)
        if not media:
            raise ValueError(f"Media with id {command.media_id} not found.")

        user_id = str(media.user_id)
        transcription = await self.transcription_repo.find_by_media_id(command.media_id)

        try:
            media.process()
            await self.media_repository.save(media)
            await self._push_update("media", media, user_id)

            if transcription and transcription.result:
                media.complete()
                await self.media_repository.save(media)
                await self._push_update("media", media, user_id)
                logger.info("transcription.completed", media_id=command.media_id, from_cache=True)
                await self.event_bus.publish(TextContentReady(media_id=str(media.id), text_content=transcription.text))
                return transcription

            if transcription is None:
                transcription = Transcription(media_id=command.media_id, provider=command.transcription_provider)
            
            transcription.process()
            transcription.provider = command.transcription_provider
            await self.transcription_repo.save(transcription)
            await self._push_update("transcription", transcription, user_id)

            audio_bytes, _ = await self.storage_service.download(command.file_path)

            breaker = get_circuit_breaker(f"transcription_{self.speech_recognition.provider_name}")
            result = await breaker.call_async(self.speech_recognition.transcribe, audio_bytes, language=command.language)

            if not result or "segments" not in result:
                raise ValueError("Transcription service returned an invalid result.")

            transcription.mark_as_completed(result)
            await self.transcription_repo.save(transcription)
            await self._push_update("transcription", transcription, user_id)
            
            media.complete()
            await self.media_repository.save(media)
            await self._push_update("media", media, user_id)

            # Publish event for summarization pipeline
            await self.event_bus.publish(TextContentReady(media_id=command.media_id, text_content=transcription.text))
            
            # Publish new event for diarization pipeline
            await self.event_bus.publish(TranscriptionWithTimestampsReady(
                media_id=command.media_id,
                audio_file_path=command.file_path,
                storage_provider=command.storage_provider,
                transcription_result=result
            ))

            duration = time.time() - start_time
            self.metrics_service.increment_transcription('success')
            self.metrics_service.observe_transcription_duration(media_id=command.media_id, duration=duration, provider=self.speech_recognition.provider_name)

            logger.info("transcription.completed", media_id=command.media_id, duration=duration)
            return transcription

        except Exception as e:
            duration = time.time() - start_time
            self.metrics_service.increment_transcription('failure')
            logger.error("transcription.failed", media_id=command.media_id, error=str(e), duration=duration)

            if media:
                media.fail(str(e)[:500])
                await self.media_repository.save(media)
                await self._push_update("media", media, user_id)

            if transcription:
                transcription.mark_as_failed(str(e)[:500])
                await self.transcription_repo.save(transcription)
                await self._push_update("transcription", transcription, user_id)

            await self.event_bus.publish(TranscriptionFailed(media_id=command.media_id, error=str(e)))
            raise
