"""SQLAlchemy models for text_analysis persistence."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB

from src.shared.infrastructure.database.db import Base


class AnalysisModel(Base):
    __tablename__ = "text_analysis_results"

    id = Column(String, primary_key=True)
    document_id = Column(String, nullable=False)

    # Foreign keys removidos para evitar dependência de criação cruzada; IDs ainda armazenados
    media_id = Column(Uuid(as_uuid=True), nullable=True, index=True)
    user_id = Column(Uuid(as_uuid=True), nullable=True, index=True)
    transcription_id = Column(Uuid(as_uuid=True), nullable=True, index=True)

    payload = Column(JSONB, nullable=False)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


__all__ = ["AnalysisModel"]
