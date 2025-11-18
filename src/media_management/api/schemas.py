# src/media_management/api/schemas.py
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.media_management.domain.media import MediaStatus, MediaType


class MediaCreate(BaseModel):
    """Schema for creating a new media item."""

    original_file_path: str = Field(
        ...,
        description="The path to the original file in storage.",
        json_schema_extra={"example": "media/user1/video.mp4"},
    )
    media_type: MediaType = Field(
        ...,
        description="The type of the media file.",
        json_schema_extra={"example": "VIDEO"},
    )


class MediaResponse(BaseModel):
    id: UUID = Field(
        ...,
        description="The unique identifier for the media item.",
        json_schema_extra={"example": "f47ac10b-58cc-4372-a567-0e02b2c3d479"},
    )
    user_id: UUID = Field(
        ...,
        description="The ID of the user who uploaded the media.",
        json_schema_extra={"example": "f47ac10b-58cc-4372-a567-0e02b2c3d479"},
    )
    original_file_path: str = Field(
        ...,
        description="The path to the original file in storage.",
        json_schema_extra={"example": "media/user1/f47ac10b.../video.mp4"},
    )
    media_type: MediaType = Field(
        ...,
        description="The type of the media file.",
        json_schema_extra={"example": "VIDEO"},
    )
    status: MediaStatus = Field(
        ...,
        description="The current processing status of the media.",
        json_schema_extra={"example": "PROCESSING"},
    )
    created_at: datetime = Field(..., description="The timestamp when the media was uploaded.")
    storage_provider: Optional[str] = Field(
        default=None,
        description="Storage provider used for the media file.",
    )
    transcription_provider: Optional[str] = Field(
        default=None,
        description="Transcription provider requested for this media.",
    )
    summarization_provider: Optional[str] = Field(
        default=None,
        description="Summarization provider selected for downstream tasks.",
    )
    sentiment_provider: Optional[str] = Field(
        default=None,
        description="Sentiment analysis provider selected for text analysis.",
    )
    topic_modeling_provider: Optional[str] = Field(
        default=None,
        description="Topic modeling provider selected for text analysis.",
    )

    model_config = ConfigDict(from_attributes=True)
