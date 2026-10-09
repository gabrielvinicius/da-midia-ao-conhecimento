"""Progresso de cada usuário nas perguntas de revisão (revisão espaçada)."""
from __future__ import annotations

import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid

from src.shared.infrastructure.database.db import Base


class ReviewProgressModel(Base):
    __tablename__ = "review_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "analysis_id", "question_key", name="uq_review_progress_question"),
    )

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), nullable=False, index=True)
    # Some com a análise (mesmo módulo), como as avaliações.
    analysis_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("text_analysis_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # sha256 do texto normalizado da pergunta (domain/review.question_key).
    question_key = Column(String(64), nullable=False)
    box = Column(Integer, nullable=False, server_default="1")
    correct_count = Column(Integer, nullable=False, server_default="0")
    wrong_count = Column(Integer, nullable=False, server_default="0")
    last_answered_at = Column(DateTime(timezone=True), nullable=False)
    due_at = Column(DateTime(timezone=True), nullable=False)


__all__ = ["ReviewProgressModel"]
