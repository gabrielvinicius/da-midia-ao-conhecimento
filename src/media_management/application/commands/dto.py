from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import UUID


@dataclass(frozen=True)
class CreateMediaCommand:
    """Encapsulates the data required to upload a new media file."""

    user_id: str
    file: bytes
    filename: str
    storage_provider: str
    transcription_provider: Optional[str] = None
    summarization_provider: Optional[str] = None
    sentiment_provider: Optional[str] = None
    topic_modeling_provider: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class DeleteMediaCommand:
    """Command to delete a media entry."""

    media_id: UUID


@dataclass(frozen=True)
class ReprocessMediaCommand:
    """Command to reprocess a media entry."""

    media_id: UUID


@dataclass(frozen=True)
class CleanupOrphanedFilesCommand:
    """Command to cleanup orphaned files in storage."""
    
    actor_id: Optional[str] = None
