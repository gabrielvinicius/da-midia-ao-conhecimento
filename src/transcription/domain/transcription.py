# src/transcription/domain/transcription.py
from sqlalchemy import Column, String, DateTime, Enum as SqlEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.hybrid import hybrid_property
from src.shared.infrastructure.database import Base
from datetime import datetime
import enum
import uuid
from typing import Dict, Any, List


class TranscriptionStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Transcription(Base):
    __tablename__ = "transcriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id"), nullable=False, unique=True)
    status = Column(SqlEnum(TranscriptionStatus), default=TranscriptionStatus.PENDING, nullable=False)
    provider = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)
    
    # Store the full, structured result from the AI provider
    result = Column(JSONB, nullable=True)
    # Store the user-defined speaker names
    speaker_aliases = Column(JSONB, nullable=True, default=lambda: {})

    @hybrid_property
    def text(self) -> str:
        """Returns the full transcribed text by joining all segments."""
        if self.result and "text" in self.result:
            return self.result.get("text", "")
        return ""

    @hybrid_property
    def segments(self) -> List[Dict[str, Any]]:
        """Returns the list of transcribed segments with timestamps."""
        if self.result and "segments" in self.result:
            return self.result.get("segments", [])
        return []

    def process(self):
        self.status = TranscriptionStatus.PROCESSING

    def mark_as_completed(self, result: Dict[str, Any]):
        self.result = result
        self.status = TranscriptionStatus.COMPLETED
        self.processed_at = datetime.utcnow()

    def mark_as_failed(self, error: str):
        self.status = TranscriptionStatus.FAILED
        self.error_message = error
        self.processed_at = datetime.utcnow()

    def set_speaker_aliases(self, aliases: Dict[str, str]):
        """Sets or updates the speaker alias map."""
        self.speaker_aliases = aliases
