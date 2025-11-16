# src/transcription/api/schemas.py
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.media_processing.transcription.domain.transcription import TranscriptionStatus


class TranscriptionResponse(BaseModel):
    """Response schema for a transcription."""

    id: UUID
    media_id: UUID
    status: TranscriptionStatus
    provider: Optional[str] = None
    created_at: datetime
    processed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    text: str
    segments: List[Dict[str, Any]]
    speaker_aliases: Dict[str, str]

    model_config = ConfigDict(from_attributes=True)


class SpeakerAliasesUpdateRequest(BaseModel):
    """Request schema for updating speaker aliases."""

    aliases: Dict[str, str] = Field(..., description="Dictionary of speaker aliases (e.g., {'speaker_0': 'John Doe'})")
