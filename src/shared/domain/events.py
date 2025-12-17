from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class DomainEvent:
    """Base event with minimal envelope metadata."""

    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=_now)
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def event_name(self) -> str:
        return self.__class__.__name__

    def with_metadata(self, **extra: Any) -> "DomainEvent":
        merged = {**self.metadata, **extra}
        return type(self)(**{**self.__dict__, "metadata": merged})


# --- Core media events ---
@dataclass
class MediaUploaded(DomainEvent):
    media_id: str = ""
    user_id: Optional[str] = None
    filename: Optional[str] = None
    media_type: Optional[str] = None
    storage_provider: Optional[str] = None
    transcription_provider: Optional[str] = None
    summarization_provider: Optional[str] = None
    sentiment_provider: Optional[str] = None
    topic_modeling_provider: Optional[str] = None
    file_path: Optional[str] = None
    file_size_bytes: Optional[int] = None
    language: Optional[str] = None


@dataclass
class MediaDeleted(DomainEvent):
    media_id: str = ""
    reason: Optional[str] = None
    user_id: Optional[str] = None
    triggered_by: Optional[str] = None
    actor_id: Optional[str] = None


@dataclass
class MediaReprocessRequested(DomainEvent):
    media_id: str = ""
    triggered_by: Optional[str] = None
    actor_id: Optional[str] = None
    requested_by: Optional[str] = None
    note: Optional[str] = None


@dataclass
class MediaProcessingStarted(DomainEvent):
    media_id: str = ""
    stage: Optional[str] = None


@dataclass
class MediaProcessingCompleted(DomainEvent):
    media_id: str = ""
    stage: Optional[str] = None
    result_id: Optional[str] = None


@dataclass
class MediaProcessingFailed(DomainEvent):
    media_id: str = ""
    stage: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class TranscriptionCompleted(DomainEvent):
    media_id: str = ""
    transcription_id: str = ""
    text_content: Optional[str] = None
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TranscriptionFailed(DomainEvent):
    media_id: str = ""
    transcription_id: Optional[str] = None
    user_id: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class TextContentReady(DomainEvent):
    media_id: str = ""
    transcription_id: Optional[str] = None
    text_content: Optional[str] = None
    user_id: Optional[str] = None
    filename: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# --- Text analysis outputs ---
@dataclass
class SummarizationCompleted(DomainEvent):
    media_id: Optional[str] = None
    transcription_id: Optional[str] = None
    summary: Optional[str] = None


@dataclass
class SentimentAnalysisCompleted(DomainEvent):
    media_id: Optional[str] = None
    transcription_id: Optional[str] = None
    sentiment_score: Optional[float] = None


@dataclass
class TopicModelingCompleted(DomainEvent):
    media_id: Optional[str] = None
    transcription_id: Optional[str] = None
    topics: Optional[Any] = None


# --- Notifications ---
@dataclass
class NotificationRequested(DomainEvent):
    user_id: Optional[str] = None
    channel: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)


__all__ = [
    "DomainEvent",
    "MediaUploaded",
    "MediaDeleted",
    "MediaReprocessRequested",
    "MediaProcessingStarted",
    "MediaProcessingCompleted",
    "MediaProcessingFailed",
    "TranscriptionCompleted",
    "TranscriptionFailed",
    "TextContentReady",
    "SummarizationCompleted",
    "SentimentAnalysisCompleted",
    "TopicModelingCompleted",
    "NotificationRequested",
]
