# src/shared/events/domain_events.py
from dataclasses import dataclass, asdict
from abc import ABC
from typing import Optional, Dict, Any

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

@dataclass(frozen=True)
class AudioExtracted(DomainEvent):
    media_id: str
    audio_file_path: str
    storage_provider: str

@dataclass(frozen=True)
class TextContentReady(DomainEvent):
    media_id: str
    text_content: str

# --- Transcription Events ---

@dataclass(frozen=True)
class TranscriptionRequested(DomainEvent):
    media_id: str
    provider: str

@dataclass(frozen=True)
class TranscriptionFailed(DomainEvent):
    media_id: str
    error: str

# --- Summarization Events ---

@dataclass(frozen=True)
class SummarizationRequested(DomainEvent):
    media_id: str
    provider: str

@dataclass(frozen=True)
class SummarizationProgress(DomainEvent):
    media_id: str
    progress: int
    stage: str
    estimated_total_seconds: Optional[float] = None

# --- Notification Events ---

@dataclass(frozen=True)
class NotificationRequested(DomainEvent):
    """An enriched event that contains all necessary data to send a notification."""
    user_id: str
    message: str
    notification_type: NotificationType
    contact_info: Dict[str, Any]
