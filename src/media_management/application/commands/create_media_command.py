# src/media_management/application/commands/create_media_command.py
"""Command definition for creating media entries."""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class CreateMediaCommand:
    """Encapsulates the data required to upload a new media file."""

    user_id: str
    file: bytes
    filename: str
    storage_provider: str
    transcription_provider: Optional[str] = None
    summarization_provider: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

