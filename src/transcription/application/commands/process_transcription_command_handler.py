# src/transcription/application/commands/process_transcription_command_handler.py
"""
Process transcription command handler following SOLID principles.
"""
import structlog

from src.media_management.application.queries.media_queries import MediaQueries
from src.storage.infrastructure.dependencies import get_storage_service_factory
from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import TextContentReady
from src.transcription.application.commands.process_transcription_command import ProcessTranscriptionCommand
from src.transcription.domain.interfaces import TranscriptionOrchestrator

logger = structlog.get_logger(__name__)


class ProcessTranscriptionCommandHandler:
    """
    Command handler for processing transcriptions following SOLID principles.
    SRP: Only handles command processing and delegation.
    DIP: Depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        orchestrator: TranscriptionOrchestrator,
        media_queries: MediaQueries,
        storage_service_factory,
        event_bus: EventBus
    ):
        self._orchestrator = orchestrator
        self._media_queries = media_queries
        self._storage_service_factory = storage_service_factory
        self._event_bus = event_bus

    async def handle(self, command: ProcessTranscriptionCommand):
        """Handle transcription command."""
        logger.info(
            "transcription.command.process_started",
            media_id=command.media_id,
            provider=command.transcription_provider,
            language=command.language
        )

        media = await self._media_queries.get_by_id(command.media_id)
        if not media:
            raise ValueError(f"Media with id {command.media_id} not found.")

        try:
            # Download audio/video file
            storage_service = self._storage_service_factory.create_storage_service("local")  # or from command
            audio_bytes, _ = await storage_service.download(command.file_path)

            if not audio_bytes:
                raise ValueError("Failed to download audio file or file is empty")

            # Get user ID for notifications
            user_id = str(media.user_id)

            # Determine if this is video or audio
            if media.media_type.value in ["VIDEO", "video"]:
                # Process video transcription
                transcription = await self._orchestrator.process_video_transcription(
                    media_id=command.media_id,
                    video_data=audio_bytes,
                    language=command.language,
                    provider=command.transcription_provider,
                    user_id=user_id
                )
            else:
                # Process audio transcription
                transcription = await self._orchestrator.process_transcription(
                    media_id=command.media_id,
                    audio_data=audio_bytes,
                    language=command.language,
                    provider=command.transcription_provider,
                    user_id=user_id
                )

            # Publish completion event for next pipeline stage
            if transcription.text:
                event = TextContentReady(
                    media_id=command.media_id,
                    text_content=transcription.text
                )
                await self._event_bus.publish(event)

            logger.info(
                "transcription.command.process_completed",
                media_id=command.media_id,
                transcription_id=str(transcription.id),
                text_length=len(transcription.text) if transcription.text else 0
            )

        except Exception as e:
            logger.error(
                "transcription.command.process_failed",
                media_id=command.media_id,
                error=str(e)
            )
            raise