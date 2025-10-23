# src/media_management/application/commands/commands.py
from dataclasses import dataclass
from typing import Dict, Any, Optional
from uuid import UUID

from src.media_management.domain.enums import MediaType


@dataclass(frozen=True)
class DeleteMediaCommand:
    """Command to delete a media entry."""
    media_id: UUID


@dataclass(frozen=True)
class ReprocessMediaCommand:
    """Command to reprocess a media entry."""
    media_id: UUID
