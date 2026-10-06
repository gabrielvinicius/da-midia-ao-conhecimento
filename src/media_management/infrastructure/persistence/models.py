"""SQLAlchemy entity definition for media records."""

import uuid

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Uuid

from src.media_management.domain.enums import MediaStatus, MediaType
from src.shared.domain.time.clock import utcnow
from src.shared.infrastructure.database.db import Base
from src.shared.infrastructure.database.types import enum_column


class MediaEntity(Base):
    __tablename__ = "media"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    original_file_path = Column(String, nullable=False)
    filename = Column(String, nullable=True)
    file_size = Column(BigInteger, nullable=True)
    mime_type = Column(String, nullable=True)
    duration = Column(Integer, nullable=True)
    media_type = Column(enum_column(MediaType), nullable=False)
    status = Column(
        enum_column(MediaStatus),
        default=MediaStatus.UPLOADED,
        nullable=False,
        index=True,
    )
    # Com fuso (UTC), como nas demais tabelas.
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, nullable=True)
    error_message = Column(String, nullable=True)

    storage_provider = Column(String, nullable=False)
    transcription_provider = Column(String, nullable=True)
    language = Column(String, nullable=True)
