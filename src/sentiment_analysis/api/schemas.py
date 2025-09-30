# src/sentiment_analysis/api/schemas.py
from pydantic import BaseModel, Field
from typing import Dict, Any
from uuid import UUID

from src.sentiment_analysis.domain.analysis import AnalysisType

class AnalysisResponse(BaseModel):
    """Schema for returning analysis information."""
    id: UUID
    media_id: UUID
    type: AnalysisType
    result: Dict[str, Any]

    class Config:
        from_attributes = True
