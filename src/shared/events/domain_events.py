# src/shared/events/domain_events.py
from dataclasses import dataclass, asdict
from abc import ABC
from typing import Optional, Dict, Any, List

from src.media_management.domain.media import MediaType
from src.notifications.domain.notification import NotificationType


@dataclass(frozen=True)
class DomainEvent(ABC):
    """Base class for domain events."""
    def to_dict(self) -> dict:
        return asdict(self)

# --- Media Pipeline Events ---

@dataclass(frozen=True)
class MediaUploaded(DomainEvent):
    media_id: str
    user_id: str
    media_type: MediaType
    file_path: str
    storage_provider: str
    transcription_provider: Optional[str] = None
    summarization_provider: Optional[str] = None

@dataclass(frozen=True)
class MediaDeleted(DomainEvent):
    media_id: str

@dataclass(frozen=True)
class AudioExtracted(DomainEvent):
    media_id: str
    audio_file_path: str
    storage_provider: str
    summarization_provider: Optional[str] = None

@dataclass(frozen=True)
class TextContentReady(DomainEvent):
    media_id: str
    text_content: str
    summarization_provider: Optional[str] = None

# --- Transcription Events ---

@dataclass(frozen=True)
class TranscriptionWithTimestampsReady(DomainEvent):
    """Event published when transcription is complete, including timestamped data."""
    media_id: str
    audio_file_path: str
    storage_provider: str
    transcription_result: Dict[str, Any]

@dataclass(frozen=True)
class TranscriptionFailed(DomainEvent):
    media_id: str
    error: str

# --- Diarization Events ---

@dataclass(frozen=True)
class DiarizationCompleted(DomainEvent):
    """Event published when speaker diarization is complete."""
    media_id: str
    diarization_result: List[Dict[str, Any]]

# --- Summarization Events ---

@dataclass(frozen=True)
class SummarizationRequested(DomainEvent):
    media_id: str
    provider: str

# --- Notification Events ---

@dataclass(frozen=True)
class NotificationRequested(DomainEvent):
    user_id: str
    message: str
    notification_type: NotificationType
    contact_info: Dict[str, Any]
