"""Core domain event definitions used across the application."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """Base value-object for all domain events."""

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def event_name(self) -> str:
        """Convenience snake_case identifier derived from the class name."""

        name = self.__class__.__name__
        parts = []
        for index, char in enumerate(name):
            if char.isupper() and index > 0:
                parts.append("_")
            parts.append(char.lower())
        return "".join(parts)

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
    media_type: Optional[Any] = None
    file_path: Optional[str] = None


@dataclass(frozen=True, slots=True)
class TextContentReady(DomainEvent):
    """Event emitted when textual artefacts derived from media are ready."""

    media_id: str = ""
    transcription_id: Optional[str] = None
    summary_id: Optional[str] = None
    sentiment_id: Optional[str] = None


if TYPE_CHECKING:
    from src.media_management.domain.media import Media


@dataclass(frozen=True, slots=True)
class MediaDeleted(DomainEvent):
    """Event emitted when a media asset is removed from the catalogue."""

    media_id: str = ""
    user_id: Optional[str] = None
    triggered_by: str = ""
    actor_id: Optional[str] = None

    @classmethod
    def for_user(cls, media: "Media", actor_id: UUID | str) -> "MediaDeleted":
        """Factory helper for user initiated deletions."""

        return cls(
            media_id=str(media.id),
            user_id=str(media.user_id),
            triggered_by="user",
            actor_id=str(actor_id),
        )


@dataclass(frozen=True, slots=True)
class MediaReprocessRequested(DomainEvent):
    """Event emitted when a media reprocess flow is requested."""

    media_id: str = ""
    triggered_by: str = ""
    actor_id: Optional[str] = None

    @classmethod
    def for_user(cls, media_id: UUID | str, actor_id: UUID | str) -> "MediaReprocessRequested":
        """Factory helper for user initiated reprocess requests."""

        return cls(
            media_id=str(media_id),
            triggered_by="user",
            actor_id=str(actor_id),
        )


__all__ = [
    "DomainEvent",
    "MediaUploaded",
    "TextContentReady",
    "MediaDeleted",
    "MediaReprocessRequested",
]
