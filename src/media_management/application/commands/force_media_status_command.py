# src/media_management/application/commands/force_media_status_command.py
from dataclasses import dataclass
from uuid import UUID

from src.media_management.domain.media import MediaStatus


@dataclass
class ForceMediaStatusCommand:
    media_id: UUID
    new_status: MediaStatus
