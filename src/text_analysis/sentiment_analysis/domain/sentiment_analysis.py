"""Domain models for the sentiment analysis module."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import Column, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB

from src.shared.infrastructure.database import Base


def _generate_id() -> str:
    """Generate a predictable identifier for domain entities."""
    return str(uuid4())


@dataclass(slots=True)
class SentimentAnalysis:
    """Aggregate root representing a sentiment analysis result."""

    id: str = field(default_factory=_generate_id)
    media_id: Optional[str] = None
    transcription_id: str = field(default_factory=_generate_id)
    overall_sentiment: str = "neutral"
    sentiment_score: float = 0.0
    confidence: Optional[float] = None
    emotions: Dict[str, float] = field(default_factory=dict)
    sentence_sentiments: List[Dict[str, Any]] = field(default_factory=list)
    provider: str = "huggingface"
    model: Optional[str] = None
    processing_time: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def update_from_payload(self, payload: Dict[str, Any]) -> None:
        """Update analysis information from a provider payload."""
        self.overall_sentiment = payload.get("overall_sentiment", self.overall_sentiment)
        self.sentiment_score = payload.get("sentiment_score", self.sentiment_score)
        self.confidence = payload.get("confidence", self.confidence)
        self.emotions = payload.get("emotions", self.emotions or {}) or {}
        self.sentence_sentiments = payload.get(
            "sentence_sentiments", self.sentence_sentiments or []
        ) or []
        self.processing_time = payload.get("processing_time", self.processing_time)
        self.updated_at = datetime.utcnow()


SentimentAnalysisResult = SentimentAnalysis


class SentimentAnalysisRecord(Base):
    """SQLAlchemy model used to persist sentiment analysis aggregates."""

    __tablename__ = "sentiment_analysis_results"

    id = Column(String, primary_key=True, default=_generate_id)
    media_id = Column(String, ForeignKey("media.id"), nullable=True)
    transcription_id = Column(
        String, ForeignKey("transcriptions.id"), nullable=False, unique=True
    )
    overall_sentiment = Column(String, nullable=False, default="neutral")
    sentiment_score = Column(Float, nullable=False, default=0.0)
    confidence = Column(Float, nullable=True)
    emotions = Column(JSONB, nullable=True)
    sentence_sentiments = Column(JSONB, nullable=True)
    provider = Column(String, nullable=False, default="huggingface")
    model = Column(String, nullable=True)
    processing_time = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_entity(self) -> SentimentAnalysis:
        """Transform the ORM record into a domain entity."""
        return SentimentAnalysis(
            id=self.id,
            media_id=self.media_id,
            transcription_id=self.transcription_id,
            overall_sentiment=self.overall_sentiment,
            sentiment_score=self.sentiment_score,
            confidence=self.confidence,
            emotions=self.emotions or {},
            sentence_sentiments=self.sentence_sentiments or [],
            provider=self.provider,
            model=self.model,
            processing_time=self.processing_time,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    @staticmethod
    def from_entity(entity: SentimentAnalysis) -> "SentimentAnalysisRecord":
        """Create a persistence record from a domain entity."""
        record = SentimentAnalysisRecord(
            id=entity.id,
            media_id=entity.media_id,
            transcription_id=entity.transcription_id,
            overall_sentiment=entity.overall_sentiment,
            sentiment_score=entity.sentiment_score,
            confidence=entity.confidence,
            emotions=entity.emotions or {},
            sentence_sentiments=entity.sentence_sentiments or [],
            provider=entity.provider,
            model=entity.model,
            processing_time=entity.processing_time,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
        return record

    def update_from_entity(self, entity: SentimentAnalysis) -> None:
        """Synchronise persistence state with the provided entity."""
        self.media_id = entity.media_id
        self.transcription_id = entity.transcription_id
        self.overall_sentiment = entity.overall_sentiment
        self.sentiment_score = entity.sentiment_score
        self.confidence = entity.confidence
        self.emotions = entity.emotions or {}
        self.sentence_sentiments = entity.sentence_sentiments or []
        self.provider = entity.provider
        self.model = entity.model
        self.processing_time = entity.processing_time
        self.updated_at = entity.updated_at


__all__ = [
    "SentimentAnalysis",
    "SentimentAnalysisRecord",
    "SentimentAnalysisResult",
]

