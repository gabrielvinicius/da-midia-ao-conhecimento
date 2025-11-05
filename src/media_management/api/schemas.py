# src/media_management/api/schemas.py
from datetime import datetime
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

    model_config = ConfigDict(from_attributes=True)
