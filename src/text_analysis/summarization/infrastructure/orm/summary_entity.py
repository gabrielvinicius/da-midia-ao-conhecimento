"""SQLAlchemy entity representing stored summaries."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum as SqlEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID

from src.shared.infrastructure.database import Base
from src.text_analysis.summarization.domain.model import SummaryStatus


class SummaryEntity(Base):
    __tablename__ = "summaries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id"), nullable=False, unique=True)
    text = Column(Text, nullable=True)
    status = Column(SqlEnum(SummaryStatus), default=SummaryStatus.PENDING, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    error_message = Column(String, nullable=True)
    provider = Column(String, nullable=True)
