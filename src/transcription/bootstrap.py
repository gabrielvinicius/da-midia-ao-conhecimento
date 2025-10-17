# src/transcription/bootstrap.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.transcription.application.queries.transcription_queries import TranscriptionQueries
from src.transcription.infrastructure.transcription_repository import TranscriptionRepository
from src.transcription.application.commands.set_speaker_aliases_command_handler import SetSpeakerAliasesCommandHandler
from src.media_management.application.queries.media_queries import MediaQueries
from src.notifications.infrastructure.connection_manager import ConnectionManager

def bootstrap_transcription_module(
    db_session: AsyncSession, 
    media_queries: MediaQueries, 
    connection_manager: ConnectionManager
) -> Dict[str, Any]:
    """Constructs and returns the services for the transcription module."""
    transcription_repository = TranscriptionRepository(db=db_session)
    transcription_queries = TranscriptionQueries(transcription_repository=transcription_repository)

    # Instantiate command handlers
    set_speaker_aliases_handler = SetSpeakerAliasesCommandHandler(
        transcription_repository=transcription_repository,
        media_queries=media_queries,
        connection_manager=connection_manager
    )

    return {
        "transcription_repository": transcription_repository,
        "transcription_queries": transcription_queries,
        "set_speaker_aliases_handler": set_speaker_aliases_handler,
    }
