"""
Topic Modeling API schemas - Following DDD pattern like transcription module
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID

class TopicModelingResponse(BaseModel):
    """Topic modeling response schema - following same pattern as transcription"""
    id: str
    media_id: UUID
    topics: List[Dict[str, Any]]
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True