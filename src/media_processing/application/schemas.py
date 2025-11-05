"""Pydantic schemas used across media processing tasks and services."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class MediaTaskPayload(BaseModel):
    """Common payload data shared across media processing tasks."""

    media_id: UUID
    file_path: str
    storage_provider: str = Field(default="local", min_length=1)
    file_size_bytes: Optional[int] = Field(default=None, ge=0)


class TranscriptionTaskPayload(MediaTaskPayload):
    """Payload specific for transcription tasks."""

    transcription_provider: str = Field(default="default", min_length=1)
    language: str = Field(default="en", min_length=2, max_length=10)


class VideoTaskPayload(MediaTaskPayload):
    """Payload specific for video processing tasks."""

    @model_validator(mode="after")
    def ensure_extension(self) -> "VideoTaskPayload":
        if not self.file_path:
            raise ValueError("file_path must be provided for video processing")
        return self


__all__ = [
    "MediaTaskPayload",
    "TranscriptionTaskPayload",
    "VideoTaskPayload",
]
