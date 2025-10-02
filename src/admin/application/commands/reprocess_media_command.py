# src/admin/application/commands/reprocess_media_command.py
from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class ReprocessMediaCommand:
    media_id: UUID
