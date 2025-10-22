# src/media_management/application/commands/commands.py
from dataclasses import dataclass
from typing import Dict, Any, Optional
from uuid import UUID

from src.media_management.domain.enums import MediaType


@dataclass(frozen=True)
class CreateMediaCommand:
    """Command to create a new media entry."""
    user_id: UUID
    original_file_path: str
    media_type: MediaType
    storage_provider: str


@dataclass(frozen=True)
class DeleteMediaCommand:
    """Command to delete a media entry."""
    media_id: UUID


@dataclass(frozen=True)
class ReprocessMediaCommand:
    """Command to reprocess a media entry."""
    media_id: UUID
