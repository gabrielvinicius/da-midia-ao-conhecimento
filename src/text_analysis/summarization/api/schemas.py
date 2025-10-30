"""
Summarization API schemas - Following DDD pattern like transcription module
"""
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from uuid import UUID

class SummaryResponse(BaseModel):
    """Summary response schema - following same pattern as transcription"""
    id: str
    media_id: UUID
    text: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
