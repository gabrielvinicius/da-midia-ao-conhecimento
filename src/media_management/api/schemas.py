# src/media_management/api/schemas.py
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from src.media_management.domain.entities.media import Media, MediaStatus, MediaType


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
    """DTO for Media responses.
    Decoupled from Domain Entities and Internal Database columns.
    """

    id: UUID = Field(..., description="The unique identifier for the media item.")
    filename: Optional[str] = Field(None, description="Original filename.")
    content_type: Optional[str] = Field(None, description="MIME type of the file.")
    size: Optional[int] = Field(None, description="File size in bytes.")
    media_type: MediaType = Field(..., description="The type of the media file.")
    status: MediaStatus = Field(..., description="The current processing status.")
    created_at: datetime = Field(
        ...,
        description="The timestamp when the media was uploaded.",
    )

    # Optional metadata
    error_message: Optional[str] = None
    language: Optional[str] = None
    duration: Optional[float] = None

    @classmethod
    def from_domain(cls, media: Media) -> "MediaResponse":
        return cls(
            id=media.id,
            filename=media.filename,
            content_type=media.mime_type,
            size=media.file_size,
            media_type=media.media_type,
            created_at=media.created_at,
            status=media.status,
            error_message=media.error_message,
            language=media.language,
            duration=media.duration,
        )

    @computed_field(return_type=List[str])
    @property
    def processing_pipeline(self) -> List[str]:
        pipeline: List[str] = ["upload"]

        if self.media_type == MediaType.VIDEO:
            pipeline.append("video_processing")
        elif self.media_type == MediaType.AUDIO:
            pipeline.append("transcription")
        elif self.media_type == MediaType.TEXT:
            pipeline.append("extract_text")

        return pipeline

    model_config = ConfigDict(from_attributes=True)
