"""Domain entity for Transcription."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.shared.domain.base_entity import AggregateRoot


class TranscriptionStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(kw_only=True)
class Transcription(AggregateRoot):
    media_id: UUID
    content: str = ""
    language: Optional[str] = None
    confidence_score: Optional[float] = None
    speaker_labels: Optional[List[Dict[str, Any]]] = None
    segments: Optional[List[Dict[str, Any]]] = None
    status: TranscriptionStatus = TranscriptionStatus.PENDING
    provider: Optional[str] = None
    # created_at, updated_at, id are inherited from AggregateRoot -> Entity
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    speaker_aliases: Dict[str, str] = field(default_factory=dict)

    @property
    def text(self) -> str:
        """Returns the stored transcription text or falls back to the raw result payload."""
        if self.content:
            return self.content
        if self.result and "text" in self.result:
            return self.result.get("text", "")
        return ""

    def process(self):
        self.status = TranscriptionStatus.PROCESSING
        self.updated_at = datetime.now(timezone.utc)

    def mark_as_completed(self, result: Dict[str, Any]):
        self.result = result
        self.content = result.get("text", "") or self.content
        self.language = result.get("language", self.language)
        self.segments = result.get("segments")
        self.speaker_labels = result.get("speaker_labels")
        self.confidence_score = result.get("confidence_score")
        self.status = TranscriptionStatus.COMPLETED
        now = datetime.now(timezone.utc)
        self.processed_at = now
        object.__setattr__(self, "updated_at", now) # Update immutable field

    def mark_as_failed(self, error: str):
        self.status = TranscriptionStatus.FAILED
        self.error_message = error
        now = datetime.now(timezone.utc)
        self.processed_at = now
        object.__setattr__(self, "updated_at", now) # Update immutable field

    def set_speaker_aliases(self, aliases: Dict[str, str]):
        """Sets or updates the speaker alias map."""
        self.speaker_aliases = aliases