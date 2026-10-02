"""SQLAlchemy models for text_analysis persistence."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, ForeignKey, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB

from src.shared.infrastructure.database.db import Base


class AnalysisModel(Base):
    __tablename__ = "text_analysis_results"

    id = Column(Uuid(as_uuid=True), primary_key=True)
    document_id = Column(Uuid(as_uuid=True), nullable=False)

    # Como as transcrições e os trechos indexados, a análise referencia a
    # mídia: a exclusão é feita pela aplicação (MediaDataEraserPort), e a
    # chave estrangeira garante que nada fique órfão.
    # Uma análise por mídia: uma nova tentativa grava sobre a anterior.
    media_id = Column(Uuid(as_uuid=True), ForeignKey("media.id"), nullable=True, index=True, unique=True)
    user_id = Column(Uuid(as_uuid=True), nullable=True, index=True)
    transcription_id = Column(Uuid(as_uuid=True), nullable=True, index=True)

    payload = Column(JSONB, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


__all__ = ["AnalysisModel"]
