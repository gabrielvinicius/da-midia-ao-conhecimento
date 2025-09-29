# src/summarization/domain/summary.py
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, DateTime, Enum as SqlEnum, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID

from src.shared.infrastructure.database import Base


class SummaryStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Summary(Base):
    __tablename__ = "summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Refactored to link to the generic Media entity
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id"), nullable=False, unique=True)
    text = Column(Text, nullable=True)
    status = Column(SqlEnum(SummaryStatus), default=SummaryStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)
    provider = Column(String, nullable=True)

    @staticmethod
    def create(media_id: str, provider: str) -> "Summary":
        """Factory method to create a new summary in a valid initial state."""
        summary = Summary(media_id=media_id, provider=provider)
        summary.status = SummaryStatus.PROCESSING
        summary.created_at = datetime.utcnow()
        return summary

    def mark_as_completed(self, content: str):
        if self.status == SummaryStatus.COMPLETED:
            return  # Avoid reprocessing
        self.text = content
        self.status = SummaryStatus.COMPLETED
        self.processed_at = datetime.utcnow()
        self.error_message = None

    def mark_as_failed(self, error: str):
        self.status = SummaryStatus.FAILED
        self.error_message = error
        self.processed_at = datetime.utcnow()
