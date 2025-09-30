# src/transcription/application/transcription_service.py
from uuid import UUID
from typing import Dict

from src.transcription.domain.transcription import Transcription
from .commands.set_speaker_aliases_command import SetSpeakerAliasesCommand
from .commands.set_speaker_aliases_command_handler import SetSpeakerAliasesCommandHandler

class TranscriptionService:
    """Facade service to dispatch transcription-related commands."""
    def __init__(self, set_speaker_aliases_handler: SetSpeakerAliasesCommandHandler):
        self.set_speaker_aliases_handler = set_speaker_aliases_handler

    async def set_speaker_aliases(self, transcription_id: UUID, aliases: Dict[str, str]) -> Transcription:
        """Dispatches the SetSpeakerAliasesCommand."""
        command = SetSpeakerAliasesCommand(transcription_id=transcription_id, aliases=aliases)
        return await self.set_speaker_aliases_handler.handle(command)
