# src/transcription/application/commands/set_speaker_aliases_command.py
from dataclasses import dataclass
from uuid import UUID
from typing import Dict

@dataclass(frozen=True)
class SetSpeakerAliasesCommand:
    """Command to set or update speaker aliases for a transcription."""
    transcription_id: UUID
    aliases: Dict[str, str]
