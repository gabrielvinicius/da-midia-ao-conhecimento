"""Pydantic schemas for sentiment analysis API responses."""

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from src.shared.api.unified_schemas import BaseResponseSchema
from src.text_analysis.sentiment_analysis.domain.sentiment_analysis import (
    SentimentAnalysis,
)


class SentimentAnalysisResponse(BaseModel):
    """Flattened sentiment analysis payload exposed to clients."""

    id: str
    media_id: Optional[str] = None
    transcription_id: str
    label: str
    score: float
    confidence: Optional[float] = None
    full_result: Dict[str, Any] = Field(default_factory=dict)
    provider: str
    model: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, analysis: SentimentAnalysis) -> "SentimentAnalysisResponse":
        """Create a DTO aligned with the frontend contract."""

        full_result: Dict[str, Any] = {
            "emotions": analysis.emotions or {},
            "sentence_sentiments": analysis.sentence_sentiments or [],
            "processing_time": analysis.processing_time,
        }
        if analysis.confidence is not None:
            full_result["confidence"] = analysis.confidence
        full_result["provider"] = analysis.provider
        if analysis.model is not None:
            full_result["model"] = analysis.model

        return cls(
            id=analysis.id,
            media_id=analysis.media_id,
            transcription_id=analysis.transcription_id,
            label=analysis.overall_sentiment,
            score=analysis.sentiment_score,
            confidence=analysis.confidence,
            full_result=full_result,
            provider=analysis.provider,
            model=analysis.model,
            created_at=analysis.created_at,
            updated_at=analysis.updated_at,
        )


class SentimentAnalysisAck(BaseModel):
    """Acknowledgement payload returned after scheduling sentiment analysis."""

    transcription_id: str
    provider: str
    model: Optional[str] = None
    status: Literal["PROCESSING"] = "PROCESSING"
    task_id: Optional[str] = None


class SentimentAnalysisAcceptedResponse(BaseResponseSchema):
    """Envelope emitted when a sentiment analysis request is accepted."""

    analysis: SentimentAnalysisAck


__all__ = [
    "SentimentAnalysisAck",
    "SentimentAnalysisAcceptedResponse",
    "SentimentAnalysisResponse",
]
