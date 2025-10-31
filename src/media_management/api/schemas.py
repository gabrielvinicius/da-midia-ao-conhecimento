# src/media_management/api/schemas.py
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime

from src.media_management.domain.media import MediaType, MediaStatus


class MediaCreate(BaseModel):
    """Schema for creating a new media item."""
    original_file_path: str = Field(..., description="The path to the original file in storage.", example="media/user1/video.mp4")
    media_type: MediaType = Field(..., description="The type of the media file.", example="VIDEO")


class MediaResponse(BaseModel):
    id: UUID = Field(..., description="The unique identifier for the media item.", example="f47ac10b-58cc-4372-a567-0e02b2c3d479")
    user_id: UUID = Field(..., description="The ID of the user who uploaded the media.", example="f47ac10b-58cc-4372-a567-0e02b2c3d479")
    original_file_path: str = Field(..., description="The path to the original file in storage.", example="media/user1/f47ac10b.../video.mp4")
    media_type: MediaType = Field(..., description="The type of the media file.", example="VIDEO")
    status: MediaStatus = Field(..., description="The current processing status of the media.", example="PROCESSING")
    created_at: datetime = Field(..., description="The timestamp when the media was uploaded.")

    class Config:
        from_attributes = True
