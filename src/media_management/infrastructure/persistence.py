"""SQLAlchemy entity definition for media records."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, Uuid
from sqlalchemy import Enum as SqlEnum

from src.shared.domain.enums import MediaStatus, MediaType
from src.shared.infrastructure.database import Base


class MediaEntity(Base):
    __tablename__ = "media"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    original_file_path = Column(String, nullable=False)
    media_type = Column(SqlEnum(MediaType), nullable=False)
    status = Column(SqlEnum(MediaStatus), default=MediaStatus.UPLOADED, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    error_message = Column(String, nullable=True)

    storage_provider = Column(String, nullable=False)
    transcription_provider = Column(String, nullable=True)
    summarization_provider = Column(String, nullable=True)
    sentiment_provider = Column(String, nullable=True)
    topic_modeling_provider = Column(String, nullable=True)
    language = Column(String, nullable=True)
