"""Domain event definitions used across the application.

These lightweight dataclasses capture the payload that flows through the
event-driven pipeline.  Each event exposes a :meth:`to_payload` helper that
normalises values (e.g. ``Enum`` instances) so that handlers can safely
consume the data as dictionaries.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, Dict, Mapping, MutableMapping, Optional

def _serialise(value: Any) -> Any:
    """Serialise dataclass values into JSON-serialisable structures."""

    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {key: _serialise(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialise(item) for item in value]
    return value


@dataclass
class DomainEvent:
    """Base class for all domain events."""

    event_name: ClassVar[str]
    occurred_on: datetime = field(default_factory=datetime.utcnow, init=False)

    def to_payload(self) -> Dict[str, Any]:
        """Return a normalised dictionary representation of the event."""

        data = asdict(self)
        data["event_name"] = self.event_name
        return {key: _serialise(value) for key, value in data.items()}


@dataclass
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


@dataclass
class AudioExtracted(DomainEvent):
    event_name: ClassVar[str] = "audio_extracted"

    media_id: str
    audio_file_path: str
    storage_provider: str
    duration: Optional[float] = None
    transcription_provider: Optional[str] = None


@dataclass
class TextContentReady(DomainEvent):
    event_name: ClassVar[str] = "text_content_ready"

    media_id: str
    text_content: str
    transcription_id: Optional[str] = None
    provider: Optional[str] = None
    language: Optional[str] = None


@dataclass
class MediaDeleted(DomainEvent):
    event_name: ClassVar[str] = "media_deleted"

    media_id: str
    reason: Optional[str] = None


@dataclass
class NotificationRequested(DomainEvent):
    event_name: ClassVar[str] = "notification_requested"

    user_id: str
    message: str
    notification_type: str
    contact_info: MutableMapping[str, Any]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SummarizationRequested(DomainEvent):
    event_name: ClassVar[str] = "summarization_requested"

    transcription_id: str
    provider: str
    strategy: Optional[str] = None


@dataclass
class SummaryCompleted(DomainEvent):
    event_name: ClassVar[str] = "summary_completed"

    summary_id: str
    transcription_id: str
    provider: Optional[str] = None
    status: Optional[str] = None


@dataclass
class SummarizationProgress(DomainEvent):
    event_name: ClassVar[str] = "summarization_progress"

    transcription_id: str
    progress: float
    message: Optional[str] = None


@dataclass
class VideoUploaded(DomainEvent):
    event_name: ClassVar[str] = "video_uploaded"

    video_id: str
    user_id: str
    file_path: str
    storage_provider: str


@dataclass
class SentimentAnalysisCompleted(DomainEvent):
    event_name: ClassVar[str] = "sentiment_analysis_completed"

    analysis_id: str
    transcription_id: str
    overall_sentiment: str
    sentiment_score: float
    confidence: Optional[float] = None
    emotions: Optional[Dict[str, float]] = None


@dataclass
class TranscriptionStarted(DomainEvent):
    event_name: ClassVar[str] = "transcription_started"

    media_id: str
    transcription_id: str
    provider: Optional[str] = None
    language: Optional[str] = None


@dataclass
class TranscriptionCompleted(DomainEvent):
    event_name: ClassVar[str] = "transcription_completed"

    media_id: str
    transcription_id: str
    text_content: str
    language: Optional[str] = None
    confidence: Optional[float] = None


@dataclass
class TranscriptionFailed(DomainEvent):
    event_name: ClassVar[str] = "transcription_failed"

    media_id: str
    error_message: str
    transcription_id: Optional[str] = None
    provider: Optional[str] = None


__all__ = [
    "DomainEvent",
    "MediaUploaded",
    "AudioExtracted",
    "TextContentReady",
    "MediaDeleted",
    "NotificationRequested",
    "SummarizationRequested",
    "SummaryCompleted",
    "SummarizationProgress",
    "VideoUploaded",
    "SentimentAnalysisCompleted",
    "TranscriptionStarted",
    "TranscriptionCompleted",
    "TranscriptionFailed",
]

