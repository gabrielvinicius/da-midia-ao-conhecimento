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

# --- Media Pipeline Events (v1) ---

@dataclass(frozen=True)
class MediaUploaded(DomainEvent):
    """A new media file has been uploaded and is ready for processing."""
    media_id: str
    user_id: str
    media_type: MediaType
    file_path: str
    storage_provider: str

@dataclass(frozen=True)
class AudioExtracted(DomainEvent):
    """Audio has been successfully extracted from a video file."""
    media_id: str
    audio_file_path: str
    storage_provider: str

@dataclass(frozen=True)
class TextContentReady(DomainEvent):
    """Text content has been generated from a media file and is ready for downstream processing (e.g., summarization)."""
    media_id: str
    text_content: str

# --- Failure & Notification Events ---

@dataclass(frozen=True)
class ProcessingFailed(DomainEvent):
    """A generic event for when any part of the pipeline fails."""
    media_id: str
    error: str

@dataclass(frozen=True)
class NotificationRequested(DomainEvent):
    user_id: str
    message: str
    notification_type: NotificationType
    contact_info: Dict[str, Any]
