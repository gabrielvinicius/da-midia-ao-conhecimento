# src/media_management/application/commands/create_media_command.py
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class CreateMediaCommand:
    user_id: str
    file: bytes
    filename: str
    storage_provider: str
    transcription_provider: Optional[str] = None
    summarization_provider: Optional[str] = None
