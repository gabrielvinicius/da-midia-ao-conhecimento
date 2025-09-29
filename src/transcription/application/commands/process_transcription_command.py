# src/transcription/application/commands/process_transcription_command.py
from dataclasses import dataclass

@dataclass(frozen=True)
class ProcessTranscriptionCommand:
    media_id: str
    file_path: str
    storage_provider: str
    transcription_provider: str
    language: str
