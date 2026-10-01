"""SQLAlchemy model for Transcription persistence."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Column, DateTime, Float, ForeignKey, String, Text, Uuid
from sqlalchemy import Enum as SqlEnum

from src.media_processing.domain import Transcription as DomainTranscription, TranscriptionStatus
from src.shared.infrastructure.database.db import Base

# Chaves, na coluna JSON "result", dos campos tipados da entidade.
MEDIA_DURATION_KEY = "media_duration_seconds"
VISUAL_CONTEXT_KEY = "visual_context"


class TranscriptionModel(Base):
    __tablename__ = "transcriptions"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("media.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    user_id = Column(Uuid(as_uuid=True), nullable=True)
    filename = Column(String, nullable=True)
    correlation_id = Column(String, nullable=True)
    content = Column(Text, nullable=False, default="")
    language = Column(String, nullable=True)
    confidence_score = Column(Float, nullable=True)
    speaker_labels = Column(JSON, nullable=True)
    segments = Column(JSON, nullable=True)
    status = Column(
        SqlEnum(TranscriptionStatus),
        default=TranscriptionStatus.PENDING,
        nullable=False,
        index=True,
    )
    provider = Column(String, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(DateTime(timezone=True), nullable=True)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String, nullable=True)
    result = Column(JSON, nullable=True)
    speaker_aliases = Column(JSON, nullable=True, default=lambda: {})

    def to_domain(self) -> DomainTranscription:
        return DomainTranscription(
            id=self.id,
            media_id=self.media_id,
            user_id=self.user_id,
            filename=self.filename,
            correlation_id=self.correlation_id,
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
            result=_raw_result(self.result),
            speaker_aliases=self.speaker_aliases,
            media_duration_seconds=(self.result or {}).get(MEDIA_DURATION_KEY),
            visual_context=(self.result or {}).get(VISUAL_CONTEXT_KEY),
        )

    @classmethod
    def from_domain(cls, transcription: DomainTranscription) -> "TranscriptionModel":
        return cls(
            id=transcription.id,
            media_id=transcription.media_id,
            user_id=getattr(transcription, "user_id", None),
            filename=getattr(transcription, "filename", None),
            correlation_id=getattr(transcription, "correlation_id", None),
            content=transcription.text,
            language=transcription.language,
            confidence_score=transcription.confidence_score,
            speaker_labels=getattr(transcription, "speaker_labels", None),
            segments=transcription.segments,
            status=transcription.status,
            provider=transcription.provider,
            created_at=transcription.created_at,
            updated_at=transcription.updated_at,
            processed_at=transcription.processed_at,
            error_message=transcription.error_message,
            result=_stored_result(transcription),
            speaker_aliases=transcription.speaker_aliases
        )


# Os campos tipados da entidade são guardados na coluna JSON "result", junto
# com a saída do modelo (detalhe de persistência, sem migração).
_TYPED_KEYS = (MEDIA_DURATION_KEY, VISUAL_CONTEXT_KEY)


def _raw_result(stored):
    if not stored:
        return stored
    raw = {k: v for k, v in stored.items() if k not in _TYPED_KEYS}
    return raw or None


def _stored_result(transcription):
    stored = dict(transcription.result or {})
    if getattr(transcription, "media_duration_seconds", None):
        stored[MEDIA_DURATION_KEY] = transcription.media_duration_seconds
    if getattr(transcription, "visual_context", None):
        stored[VISUAL_CONTEXT_KEY] = list(transcription.visual_context)
    return stored or None
