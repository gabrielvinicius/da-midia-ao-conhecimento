from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from uuid import UUID


class RequestTranscriptionCommand(BaseModel):
    media_id: UUID = Field(..., description="ID of the media to transcribe.")
    file_path: str = Field(..., description="Path to the media file in storage.")
    storage_provider: str = Field(..., description="Provider where the media file is stored.")
    transcription_provider: str = Field(..., description="Provider to use for transcription.")
    language: str = Field(..., description="Language of the media content.")
    file_size_bytes: int = Field(0, ge=0, description="Size of the media file in bytes.")
    summarization_provider: Optional[str] = Field(None, description="Provider to use for summarization.")
    sentiment_provider: Optional[str] = Field(None, description="Provider to use for sentiment analysis.")
    topic_modeling_provider: Optional[str] = Field(None, description="Provider to use for topic modeling.")
    
    class Config:
        frozen = True


class RequestVideoProcessingCommand(BaseModel):
    media_id: UUID = Field(..., description="ID of the media to process.")
    file_path: str = Field(..., description="Path to the video file in storage.")
    storage_provider: str = Field(..., description="Provider where the video file is stored.")

    class Config:
        frozen = True


class SetSpeakerAliasesCommand(BaseModel):
    transcription_id: UUID = Field(..., description="ID of the transcription to update.")
    aliases: Dict[str, str] = Field(..., description="Mapping of speaker IDs to their aliases.")

    class Config:
        frozen = True


class ReprocessTranscriptionCommand(BaseModel):
    media_id: UUID = Field(..., description="ID of the media associated with the transcription to reprocess.")
    provider: Optional[str] = Field(None, description="Provider to use for reprocessing.")
    language: str = Field("auto", description="Language code for reprocessing.")
    force: bool = Field(False, description="Force reprocessing even if already completed.")
    user_id: UUID = Field(..., description="ID of the user initiating the reprocess.") # Needed for auth check

    class Config:
        frozen = True