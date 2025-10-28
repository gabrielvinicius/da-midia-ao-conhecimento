# src/media_management/application/commands/commands.py
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class DeleteMediaCommand:
    """Command to delete a media entry."""
    media_id: UUID


@dataclass(frozen=True)
class ReprocessMediaCommand:
    """Command to reprocess a media entry."""
    media_id: UUID
