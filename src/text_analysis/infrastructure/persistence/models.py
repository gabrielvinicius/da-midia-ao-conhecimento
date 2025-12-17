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

    media_id = Column(Uuid(as_uuid=True), ForeignKey("media.id"), nullable=True, index=True)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    transcription_id = Column(Uuid(as_uuid=True), ForeignKey("transcriptions.id"), nullable=True, index=True)

    payload = Column(JSONB, nullable=False)


__all__ = ["AnalysisModel"]
