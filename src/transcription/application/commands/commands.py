"""
Transcription Commands - Pure data classes following Command Pattern
"""
from dataclasses import dataclass
from typing import Dict, Any
from uuid import UUID


@dataclass(frozen=True)
class ProcessTranscriptionCommand:
    """Command to process transcription"""
    media_id: str
    file_path: str
    storage_provider: str
    transcription_provider: str
    language: str


@dataclass(frozen=True)
class SetSpeakerAliasesCommand:
    """Command to set speaker aliases"""
    transcription_id: UUID
    aliases: Dict[str, str]