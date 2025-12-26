from __future__ import annotations

import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from src.shared.domain.base_entity import BaseEntity


class TranscriptionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Transcription(BaseEntity):
    """Transcription aggregate root."""

    media_id: UUID
    user_id: Optional[UUID]
    filename: Optional[str]
    correlation_id: Optional[str]
    language: str
    text: str
    segments: list[Dict[str, Any]]
    speaker_labels: list[Dict[str, Any]]
    confidence_score: float
    provider: str
    status: TranscriptionStatus
    created_at: datetime.datetime
    updated_at: datetime.datetime
    error_message: Optional[str]
    speaker_aliases: Dict[str, str]
    processed_at: Optional[datetime.datetime]
    result: Optional[Dict[str, Any]]

    def __init__(
        self,
        media_id: UUID,
        user_id: Optional[UUID] = None,
        filename: Optional[str] = None,
        correlation_id: Optional[str] = None,
        language: str = "auto",
        content: Optional[str] = None,
        text: str = "",
        segments: Optional[list[Dict[str, Any]]] = None,
        speaker_labels: Optional[list[Dict[str, Any]]] = None,
        confidence_score: float = 0.0,
        provider: str = "default",
        status: TranscriptionStatus = TranscriptionStatus.PENDING,
        created_at: Optional[datetime.datetime] = None,
        updated_at: Optional[datetime.datetime] = None,
        error_message: Optional[str] = None,
        speaker_aliases: Optional[Dict[str, str]] = None,
        result: Optional[Dict[str, Any]] = None,
        processed_at: Optional[datetime.datetime] = None,
        id: Optional[UUID] = None,
    ):
        super().__init__(id or uuid4())
        self.media_id = media_id
        self.user_id = user_id
        self.filename = filename
        self.correlation_id = correlation_id
        self.language = language
        self.text = text or content or ""
        self.segments = segments or []
        self.speaker_labels = speaker_labels or []
        self.confidence_score = confidence_score
        self.provider = provider
        self.status = status
        self.created_at = created_at or datetime.datetime.now(datetime.timezone.utc)
        self.updated_at = updated_at or datetime.datetime.now(datetime.timezone.utc)
        self.error_message = error_message
        self.speaker_aliases = speaker_aliases or {}
        self.processed_at: Optional[datetime.datetime] = processed_at
        self.result = result

    def mark_as_completed(self, result: Dict[str, Any]) -> None:
        self.status = TranscriptionStatus.COMPLETED
        self.text = result.get("text", "")
        self.segments = result.get("segments", [])
        self.speaker_labels = result.get("speaker_labels", self.speaker_labels)
        self.language = result.get("language", self.language)
        self.confidence_score = result.get("confidence_score") or result.get(
            "confidence", 0.0
        )
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)
        self.processed_at = self.updated_at
        self.result = result or self.result

    def mark_as_processing(self) -> None:
        self.status = TranscriptionStatus.PROCESSING
        self.error_message = None
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)

    def record_processing_error(self, error_message: str) -> None:
        self.status = TranscriptionStatus.PROCESSING
        self.error_message = error_message
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)

    def mark_as_failed(self, error_message: str) -> None:
        self.status = TranscriptionStatus.FAILED
        self.error_message = error_message
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)
        self.processed_at = self.updated_at

    def set_speaker_aliases(self, aliases: Dict[str, str]) -> None:
        self.speaker_aliases = aliases
        self.updated_at = datetime.datetime.now(datetime.timezone.utc)
