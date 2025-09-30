# src/media_management/application/commands/reprocess_media_command.py
from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class ReprocessMediaCommand:
    """Command to re-trigger the processing pipeline for a media item."""
    media_id: UUID
