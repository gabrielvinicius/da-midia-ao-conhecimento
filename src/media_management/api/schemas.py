# src/media_management/api/schemas.py
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

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
    language: Optional[str] = Field(
        default=None,
        description="Idioma detectado ou configurado para a mídia.",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Mensagem de erro associada ao processamento, quando houver.",
    )

    @computed_field(return_type=List[str])
    @property
    def processing_pipeline(self) -> List[str]:
        pipeline: List[str] = ["upload"]

        if self.media_type == MediaType.VIDEO:
            pipeline.append("video_processing")

        if self.media_type == MediaType.TEXT:
            pipeline.append("extract_text")
        else:
            pipeline.append("transcription")

        if self.summarization_provider:
            pipeline.append("summarization")
        if self.sentiment_provider:
            pipeline.append("sentiment")
        if self.topic_modeling_provider:
            pipeline.append("topic_modeling")

        return pipeline

    model_config = ConfigDict(from_attributes=True)
