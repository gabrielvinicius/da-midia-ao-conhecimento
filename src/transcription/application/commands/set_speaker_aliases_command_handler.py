# src/transcription/application/commands/set_speaker_aliases_command_handler.py
import structlog
import json

from src.transcription.infrastructure.transcription_repository import TranscriptionRepository
from src.transcription.domain.transcription import Transcription
from src.media_management.application.queries.media_queries import MediaQueries
from src.notifications.infrastructure.connection_manager import ConnectionManager
from .set_speaker_aliases_command import SetSpeakerAliasesCommand

logger = structlog.get_logger(__name__)

class SetSpeakerAliasesCommandHandler:
    def __init__(
        self, 
        transcription_repository: TranscriptionRepository,
        media_queries: MediaQueries,
        connection_manager: ConnectionManager
    ):
        self.transcription_repo = transcription_repository
        self.media_queries = media_queries
        self.connection_manager = connection_manager

    async def handle(self, command: SetSpeakerAliasesCommand) -> Transcription:
        """Handles setting speaker aliases for a transcription."""
        transcription_id_str = str(command.transcription_id)
        logger.info("transcription.set_aliases.started", transcription_id=transcription_id_str)

        transcription = await self.transcription_repo.find_by_id(transcription_id_str)
        if not transcription:
            raise ValueError(f"Transcription with id {transcription_id_str} not found.")

        transcription.set_speaker_aliases(command.aliases)

        updated_transcription = await self.transcription_repo.save(transcription)

        # Push the update to the frontend
        media = await self.media_queries.get_by_id(str(transcription.media_id))
        if media:
            message = {
                "type": "entity_update",
                "entity": "transcription",
                "payload": json.loads(updated_transcription.model_dump_json())
            }
            await self.connection_manager.send_personal_message(json.dumps(message), str(media.user_id))
        
        logger.info("transcription.set_aliases.completed", transcription_id=transcription_id_str)
        return updated_transcription
