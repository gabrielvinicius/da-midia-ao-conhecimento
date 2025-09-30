# src/transcription/api/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from src.transcription.domain.transcription import TranscriptionStatus


class SpeakerAliasesUpdateRequest(BaseModel):
    """Schema for updating speaker aliases."""
    aliases: Dict[str, str] = Field(..., description="A map of speaker IDs to custom names.", example={"SPEAKER_00": "Alice", "SPEAKER_01": "Bob"})


class TranscriptionResponse(BaseModel):
    """Schema for returning transcription information."""
    id: UUID
    media_id: UUID
    status: TranscriptionStatus
    provider: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    
    # Return the full structured result and aliases
    result: Optional[Dict[str, Any]] = None
    speaker_aliases: Optional[Dict[str, str]] = None

    class Config:
        from_attributes = True
