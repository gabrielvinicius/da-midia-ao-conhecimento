# src/transcription/application/commands/process_transcription_command_handler.py
import time
import structlog

from src.metrics.application.metrics_service import MetricsService
from src.media_management.application.queries.media_queries import MediaQueries
from .process_transcription_command import ProcessTranscriptionCommand

# Import the new SRP-compliant services
from ..services.transcription_state_service import TranscriptionStateService
from ..services.transcription_file_service import TranscriptionFileService
from ..services.speech_recognition_service import SpeechRecognitionService
from ..services.transcription_event_service import TranscriptionEventService

logger = structlog.get_logger(__name__)


class ProcessTranscriptionCommandHandler:
    """
    Orchestrates the transcription process by coordinating with specialized services.
    """
    def __init__(
        self,
        media_queries: MediaQueries,
        state_service: TranscriptionStateService,
        file_service: TranscriptionFileService,
        recognition_service: SpeechRecognitionService,
        event_service: TranscriptionEventService,
        metrics_service: MetricsService,
    ):
        self.media_queries = media_queries
        self.state_service = state_service
        self.file_service = file_service
        self.recognition_service = recognition_service
        self.event_service = event_service
        self.metrics_service = metrics_service

    async def handle(self, command: ProcessTranscriptionCommand):
        start_time = time.time()
        logger.info("transcription.started", media_id=command.media_id, provider=command.transcription_provider)

        media = await self.media_queries.get_by_id(command.media_id)
        if not media:
            raise ValueError(f"Media with id {command.media_id} not found.")

        try:
            # 1. Set initial state
            transcription = await self.state_service.start_processing(
                media, command.language, command.transcription_provider
            )

            # 2. Download audio file
            audio_bytes = await self.file_service.download_audio(command.file_path)

            # 3. Perform speech-to-text
            text = await self.recognition_service.transcribe(audio_bytes, command.language)

            # 4. Set final state
            await self.state_service.complete_processing(media, transcription, text)

            # 5. Publish completion event
            await self.event_service.publish_completion_event(command.media_id, text)

            # 6. Record metrics
            duration = time.time() - start_time
            self.metrics_service.increment_transcription('success')
            self.metrics_service.observe_transcription_duration(
                media_id=command.media_id, 
                duration=duration, 
                provider=command.transcription_provider
            )
            logger.info("transcription.completed", media_id=command.media_id, duration=duration)

        except Exception as e:
            duration = time.time() - start_time
            self.metrics_service.increment_transcription('failure')
            logger.error("transcription.failed", media_id=command.media_id, error=str(e), duration=duration)

            # 4a. Set failure state
            await self.state_service.fail_processing(media, str(e))

            # 5a. Publish failure event
            await self.event_service.publish_failure_event(command.media_id, str(e))
            
            raise