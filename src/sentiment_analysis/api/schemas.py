"""
Sentiment Analysis API schemas - Following DDD pattern like transcription module
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

class SentimentAnalysisResponse(BaseModel):
    """Sentiment analysis response schema - following same pattern as transcription"""
    id: str
    media_id: UUID
    sentiment: str
    confidence: float
    details: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True