# src/transcription/domain/transcription.py
import enum
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.hybrid import hybrid_property

from src.shared.infrastructure.database import Base


class TranscriptionStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Transcription(Base):
    __tablename__ = "transcriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id"), nullable=False, unique=True)
    content = Column(Text, nullable=False, default="")
    language = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    speaker_labels = Column(JSONB, nullable=True)
    segments = Column(JSONB, nullable=True)
    status = Column(SqlEnum(TranscriptionStatus), default=TranscriptionStatus.PENDING, nullable=False)
    provider = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String, nullable=True)

    # Store the full, structured result from the AI provider
    result = Column(JSONB, nullable=True)
    # Store the user-defined speaker names
    speaker_aliases = Column(JSONB, nullable=True, default=lambda: {})

    @hybrid_property
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
        self.updated_at = now

    def mark_as_failed(self, error: str):
        self.status = TranscriptionStatus.FAILED
        self.error_message = error
        now = datetime.now(timezone.utc)
        self.processed_at = now
        self.updated_at = now

    def set_speaker_aliases(self, aliases: Dict[str, str]):
        """Sets or updates the speaker alias map."""
        self.speaker_aliases = aliases
