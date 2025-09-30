# src/topic_modeling/api/schemas.py
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import List

class TopicModelingResponse(BaseModel):
    """Schema for returning topic modeling results."""
    id: UUID = Field(..., description="The unique identifier for the analysis record.")
    media_id: UUID = Field(..., description="The ID of the media item that was analyzed.")
    topics: List[str] = Field(..., description="A list of extracted topics or keywords.", example=["Topic #1: technology, software, engineering", "Topic #2: architecture, design, patterns"])
    created_at: datetime = Field(..., description="The timestamp when the analysis was completed.")

    class Config:
        from_attributes = True
