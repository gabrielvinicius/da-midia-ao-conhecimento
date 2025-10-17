"""
Transcription Command Handlers - Pure execution logic following Command Pattern
"""
import json
import structlog
from typing import Dict, Any

from src.media_management.application.queries.media_queries import MediaQueries
from src.storage.infrastructure.dependencies import get_storage_service_factory
from src.shared.events.event_bus import EventBus
from src.shared.events.domain_events import TextContentReady
from src.transcription.domain.interfaces import TranscriptionOrchestrator
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository
from src.notifications.infrastructure.connection_manager import ConnectionManager
from .commands import (
    ProcessTranscriptionCommand,
    SetSpeakerAliasesCommand
)

logger = structlog.get_logger(__name__)


class ProcessTranscriptionCommandHandler:
    """Handler for process transcription command"""
    
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

    async def handle(self, command: ProcessTranscriptionCommand) -> Dict[str, Any]:
        """Execute transcription processing command"""
        logger.info(
            "transcription.command.process_started",
            media_id=command.media_id,
            provider=command.transcription_provider,
            language=command.language
        )

        try:
            media = await self._media_queries.get_by_id(command.media_id)
            if not media:
                return {
                    "success": False,
                    "error": f"Media with id {command.media_id} not found",
                    "message": "Media not found"
                }

            # Download audio/video file
            storage_service = self._storage_service_factory.create_storage_service("local")
            audio_bytes, _ = await storage_service.download(command.file_path)

            if not audio_bytes:
                return {
                    "success": False,
                    "error": "Failed to download audio file or file is empty",
                    "message": "Audio download failed"
                }

            user_id = str(media.user_id)

            # Process transcription based on media type
            if media.media_type.value in ["VIDEO", "video"]:
                transcription = await self._orchestrator.process_video_transcription(
                    media_id=command.media_id,
                    video_data=audio_bytes,
                    language=command.language,
                    provider=command.transcription_provider,
                    user_id=user_id
                )
            else:
                transcription = await self._orchestrator.process_transcription(
                    media_id=command.media_id,
                    audio_data=audio_bytes,
                    language=command.language,
                    provider=command.transcription_provider,
                    user_id=user_id
                )

            # Publish completion event
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

            return {
                "success": True,
                "transcription": {
                    "id": str(transcription.id),
                    "media_id": command.media_id,
                    "text": transcription.text,
                    "language": command.language,
                    "provider": command.transcription_provider
                },
                "message": "Transcription processed successfully"
            }

        except Exception as e:
            logger.error(
                "transcription.command.process_failed",
                media_id=command.media_id,
                error=str(e)
            )
            return {
                "success": False,
                "error": str(e),
                "message": f"Transcription processing failed: {str(e)}"
            }


class SetSpeakerAliasesCommandHandler:
    """Handler for set speaker aliases command"""
    
    def __init__(
        self, 
        transcription_repository: TranscriptionRepository,
        media_queries: MediaQueries,
        connection_manager: ConnectionManager
    ):
        self.transcription_repo = transcription_repository
        self.media_queries = media_queries
        self.connection_manager = connection_manager

    async def handle(self, command: SetSpeakerAliasesCommand) -> Dict[str, Any]:
        """Execute set speaker aliases command"""
        transcription_id_str = str(command.transcription_id)
        logger.info("transcription.set_aliases.started", transcription_id=transcription_id_str)

        try:
            transcription = await self.transcription_repo.find_by_id(transcription_id_str)
            if not transcription:
                return {
                    "success": False,
                    "error": f"Transcription with id {transcription_id_str} not found",
                    "message": "Transcription not found"
                }

            transcription.set_speaker_aliases(command.aliases)
            updated_transcription = await self.transcription_repo.save(transcription)

            # Push update to frontend
            media = await self.media_queries.get_by_id(str(transcription.media_id))
            if media:
                message = {
                    "type": "entity_update",
                    "entity": "transcription",
                    "payload": json.loads(updated_transcription.model_dump_json())
                }
                await self.connection_manager.send_personal_message(json.dumps(message), str(media.user_id))
            
            logger.info("transcription.set_aliases.completed", transcription_id=transcription_id_str)
            
            return {
                "success": True,
                "transcription": {
                    "id": str(updated_transcription.id),
                    "aliases": command.aliases
                },
                "message": "Speaker aliases updated successfully"
            }

        except Exception as e:
            logger.error("transcription.set_aliases.failed", 
                        transcription_id=transcription_id_str, 
                        error=str(e))
            return {
                "success": False,
                "error": str(e),
                "message": f"Failed to set speaker aliases: {str(e)}"
            }