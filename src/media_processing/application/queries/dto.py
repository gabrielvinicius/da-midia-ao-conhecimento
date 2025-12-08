from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class GetTranscriptionByMediaIdQuery(BaseModel):
    media_id: UUID = Field(..., description="ID of the media to get transcription for.")
    
    class Config:
        frozen = True


class GetTranscriptionByIdQuery(BaseModel):
    transcription_id: UUID = Field(..., description="ID of the transcription to retrieve.")
    
    class Config:
        frozen = True
