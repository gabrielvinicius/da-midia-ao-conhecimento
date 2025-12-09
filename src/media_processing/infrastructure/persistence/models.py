"""SQLAlchemy model for Transcription persistence."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text, Uuid
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import JSON

from src.shared.infrastructure.database.db import Base
from src.media_processing.domain.model import (
    Transcription as DomainTranscription,
    TranscriptionStatus,
)


class TranscriptionModel(Base):
    __tablename__ = "transcriptions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(Uuid(as_uuid=True), ForeignKey("media.id"), nullable=False, unique=True, index=True)
    content = Column(Text, nullable=False, default="")
    language = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    speaker_labels = Column(JSON, nullable=True)
    segments = Column(JSON, nullable=True)
    status = Column(SqlEnum(TranscriptionStatus), default=TranscriptionStatus.PENDING, nullable=False, index=True)
    provider = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String, nullable=True)
    result = Column(JSON, nullable=True)
    speaker_aliases = Column(JSON, nullable=True, default=lambda: {})

    def to_domain(self) -> DomainTranscription:
        return DomainTranscription(
            id=self.id,
            media_id=self.media_id,
            content=self.content,
            language=self.language,
            confidence_score=self.confidence_score,
            speaker_labels=self.speaker_labels,
            segments=self.segments,
            status=self.status,
            provider=self.provider,
            created_at=self.created_at,
            updated_at=self.updated_at,
            processed_at=self.processed_at,
            error_message=self.error_message,
            result=self.result,
            speaker_aliases=self.speaker_aliases
        )

    @classmethod
    def from_domain(cls, transcription: DomainTranscription) -> "TranscriptionModel":
        return cls(
            id=transcription.id,
            media_id=transcription.media_id,
            content=transcription.content,
            language=transcription.language,
            confidence_score=transcription.confidence_score,
            speaker_labels=transcription.speaker_labels,
            segments=transcription.segments,
            status=transcription.status,
            provider=transcription.provider,
            created_at=transcription.created_at,
            updated_at=transcription.updated_at,
            processed_at=transcription.processed_at,
            error_message=transcription.error_message,
            result=transcription.result,
            speaker_aliases=transcription.speaker_aliases
        )