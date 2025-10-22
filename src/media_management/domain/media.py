# src/media_management/domain/media.py
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, String, Enum as SqlEnum, DateTime, ForeignKey, event
from sqlalchemy.dialects.postgresql import UUID

from src.shared.infrastructure.database import Base

from .enums import MediaType, MediaStatus

class Media(Base):
    __tablename__ = "media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    original_file_path = Column(String, nullable=False)
    media_type = Column(SqlEnum(MediaType), nullable=False)
    status = Column(SqlEnum(MediaStatus), default=MediaStatus.UPLOADED, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    error_message = Column(String, nullable=True)
    
    # Provider choices made at upload time
    storage_provider = Column(String, nullable=False)
    transcription_provider = Column(String, nullable=True)
    summarization_provider = Column(String, nullable=True)
    language = Column(String, nullable=True) # Added language field

    def process(self):
        self.status = MediaStatus.PROCESSING
        self.error_message = None

    def complete(self):
        self.status = MediaStatus.COMPLETED
        self.error_message = None

    def fail(self, reason: str):
        self.status = MediaStatus.FAILED
        self.error_message = reason