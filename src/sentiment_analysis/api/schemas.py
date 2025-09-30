# src/sentiment_analysis/api/schemas.py
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Dict, Any

class SentimentAnalysisResponse(BaseModel):
    """Schema for returning sentiment analysis results."""
    id: UUID = Field(..., description="The unique identifier for the analysis record.")
    media_id: UUID = Field(..., description="The ID of the media item that was analyzed.")
    label: str = Field(..., description="The overall sentiment label.", example="POSITIVE")
    score: float = Field(..., description="The confidence score of the sentiment label.", example=0.998)
    full_result: Dict[str, Any] = Field(..., description="The raw result from the analysis provider.")
    created_at: datetime = Field(..., description="The timestamp when the analysis was completed.")

    class Config:
        from_attributes = True
