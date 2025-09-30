# src/transcription/application/commands/align_diarization_command_handler.py
import structlog
import json

from src.transcription.infrastructure.transcription_repository import TranscriptionRepository
from src.transcription.domain.transcription import Transcription
from src.media_management.application.queries.media_queries import MediaQueries
from src.notifications.infrastructure.connection_manager import ConnectionManager
from ..services.alignment_service import AlignmentService
from .align_diarization_command import AlignDiarizationCommand

logger = structlog.get_logger(__name__)

class AlignDiarizationCommandHandler:
    def __init__(
        self, 
        transcription_repository: TranscriptionRepository, 
        media_queries: MediaQueries,
        alignment_service: AlignmentService,
        connection_manager: ConnectionManager
    ):
        self.transcription_repo = transcription_repository
        self.media_queries = media_queries
        self.alignment_service = alignment_service
        self.connection_manager = connection_manager

    async def handle(self, command: AlignDiarizationCommand) -> Transcription:
        """Handles the alignment of diarization and transcription data."""
        media_id_str = str(command.media_id)
        logger.info("diarization.alignment.started", media_id=media_id_str)

        transcription = await self.transcription_repo.find_by_media_id(media_id_str)
        if not transcription or not transcription.result:
            raise ValueError(f"Transcription for media id {media_id_str} not found or has no result.")

        # Perform the alignment
        aligned_segments = self.alignment_service.align(
            transcription_result=transcription.result,
            diarization_result=command.diarization_result
        )

        # Update the transcription result with the new aligned segments
        # We add a new key 'aligned_segments' to preserve the original data if needed
        transcription.result['segments'] = aligned_segments
        transcription.result['diarized'] = True # Add a flag to indicate completion

        # Save the final result
        updated_transcription = await self.transcription_repo.save(transcription)

        # Push the final, updated transcription to the frontend
        media = await self.media_queries.get_by_id(media_id_str)
        if media:
            message = {
                "type": "entity_update",
                "entity": "transcription",
                "payload": json.loads(updated_transcription.model_dump_json())
            }
            await self.connection_manager.send_personal_message(json.dumps(message), str(media.user_id))
        
        logger.info("diarization.alignment.completed", media_id=media_id_str)
        return updated_transcription
