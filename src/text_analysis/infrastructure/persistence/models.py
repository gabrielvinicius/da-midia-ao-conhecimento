"""SQLAlchemy models for text_analysis persistence."""

from __future__ import annotations

import uuid
from sqlalchemy import Column, ForeignKey, String, Uuid
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


__all__ = ["AnalysisModel"]
