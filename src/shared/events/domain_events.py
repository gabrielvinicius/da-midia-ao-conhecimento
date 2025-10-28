"""Domain event definitions used across the application."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, ClassVar, Dict, Mapping, MutableMapping, Optional
from uuid import UUID, uuid4


def _serialise(value: Any) -> Any:
    """Serialise dataclass values into JSON-serialisable structures."""

    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Mapping):
        return {key: _serialise(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialise(item) for item in value]
    return value


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    """Base class for all domain events."""

    event_name: ClassVar[str] = "domain_event"
    event_id: UUID = field(default_factory=uuid4, kw_only=True)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc), kw_only=True)
    metadata: Mapping[str, Any] = field(default_factory=dict, kw_only=True)

    def to_payload(self) -> Dict[str, Any]:
        """Return a normalised dictionary representation of the event."""

        data = asdict(self)
        data["event_name"] = self.event_name
        data["event_id"] = str(self.event_id)
        data["occurred_at"] = self.occurred_at.isoformat()
        data["metadata"] = dict(self.metadata)
        return {key: _serialise(value) for key, value in data.items()}


@dataclass(frozen=True, kw_only=True)
class MediaUploaded(DomainEvent):
    event_name: ClassVar[str] = "media_uploaded"

    media_id: str
    user_id: str
    media_type: Enum
    file_path: str
    storage_provider: str
    transcription_provider: Optional[str] = None
    summarization_provider: Optional[str] = None
    text_content: Optional[str] = None
    processing_type: Optional[str] = None


@dataclass(frozen=True, kw_only=True)
class AudioExtracted(DomainEvent):
    event_name: ClassVar[str] = "audio_extracted"

    media_id: str
    audio_file_path: str
    storage_provider: str
    duration: Optional[float] = None
    transcription_provider: Optional[str] = None


@dataclass(frozen=True, kw_only=True)
class TextContentReady(DomainEvent):
    event_name: ClassVar[str] = "text_content_ready"

    media_id: str
    text_content: str
    transcription_id: Optional[str] = None
    provider: Optional[str] = None
    language: Optional[str] = None


@dataclass(frozen=True, kw_only=True)
class MediaDeleted(DomainEvent):
    event_name: ClassVar[str] = "media_deleted"

    media_id: str
    reason: Optional[str] = None


@dataclass(frozen=True, kw_only=True)
class NotificationRequested(DomainEvent):
    event_name: ClassVar[str] = "notification_requested"

    user_id: str
    message: str
    notification_type: str
    contact_info: MutableMapping[str, Any]
    metadata: Optional[Dict[str, Any]] = None


@dataclass(frozen=True, kw_only=True)
class SummarizationRequested(DomainEvent):
    event_name: ClassVar[str] = "summarization_requested"

    transcription_id: str
    provider: str
    strategy: Optional[str] = None


__all__ = [
    "DomainEvent",
    "MediaUploaded",
    "AudioExtracted",
    "TextContentReady",
    "MediaDeleted",
    "NotificationRequested",
    "SummarizationRequested",
]
