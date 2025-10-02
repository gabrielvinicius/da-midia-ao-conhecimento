# src/media_management/application/commands/delete_media_command.py
from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class DeleteMediaCommand:
    media_id: UUID
