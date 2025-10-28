"""Pydantic schemas for sentiment analysis API responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.sentiment_analysis.domain.sentiment_analysis import SentimentAnalysis


class SentimentAnalysisResponse(BaseModel):
    """API representation of a ``SentimentAnalysis`` aggregate."""

    id: str
    media_id: Optional[str] = None
    transcription_id: str
    overall_sentiment: str
    sentiment_score: float
    confidence: Optional[float] = None
    emotions: Dict[str, float] = Field(default_factory=dict)
    sentence_sentiments: List[Dict[str, Any]] = Field(default_factory=list)
    provider: str
    model: Optional[str] = None
    processing_time: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, analysis: SentimentAnalysis) -> "SentimentAnalysisResponse":
        return cls(
            id=analysis.id,
            media_id=analysis.media_id,
            transcription_id=analysis.transcription_id,
            overall_sentiment=analysis.overall_sentiment,
            sentiment_score=analysis.sentiment_score,
            confidence=analysis.confidence,
            emotions=analysis.emotions,
            sentence_sentiments=analysis.sentence_sentiments,
            provider=analysis.provider,
            model=analysis.model,
            processing_time=analysis.processing_time,
            created_at=analysis.created_at,
            updated_at=analysis.updated_at,
        )


__all__ = ["SentimentAnalysisResponse"]

