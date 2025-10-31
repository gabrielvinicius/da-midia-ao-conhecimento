"""Core domain event definitions used across the application."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Base value-object for all domain events."""

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    def with_metadata(self, **extra: Any) -> "DomainEvent":
        """Return a new event instance enriched with metadata."""
        merged = {**self.metadata, **extra}
        return replace(self, metadata=merged)


@dataclass(frozen=True, slots=True)
class MediaUploaded(DomainEvent):
    """Event emitted when a media asset is uploaded."""

    media_id: str = ""
    user_id: str = ""
    storage_provider: Optional[str] = None
    filename: Optional[str] = None


@dataclass(frozen=True, slots=True)
class TextContentReady(DomainEvent):
    """Event emitted when textual artefacts derived from media are ready."""

    media_id: str = ""
    transcription_id: Optional[str] = None
    summary_id: Optional[str] = None
    sentiment_id: Optional[str] = None


__all__ = [
    "DomainEvent",
    "MediaUploaded",
    "TextContentReady",
]
