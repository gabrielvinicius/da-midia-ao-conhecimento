# src/transcription/api/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime

# Import the status enum from the domain layer to ensure consistency
from src.transcription.domain.transcription import TranscriptionStatus


class TranscriptionResponse(BaseModel):
    """Schema for returning transcription information."""
    id: UUID = Field(..., description="The unique identifier for the transcription record.", example="a1b2c3d4-e5f6-7890-1234-567890abcdef")
    media_id: UUID = Field(..., description="The ID of the media item this transcription belongs to.", example="f47ac10b-58cc-4372-a567-0e02b2c3d479")
    text: Optional[str] = Field(None, description="The full transcribed text.", example="This is the transcribed text from the audio.")
    status: TranscriptionStatus = Field(..., description="The current status of the transcription process.", example="COMPLETED")
    provider: Optional[str] = Field(None, description="The service provider used for this transcription.", example="whisper")
    created_at: datetime = Field(..., description="The timestamp when the transcription process was initiated.")
    processed_at: Optional[datetime] = Field(None, description="The timestamp when the transcription process was completed or failed.")
    error_message: Optional[str] = Field(None, description="Any error message if the transcription failed.")

    class Config:
        from_attributes = True
