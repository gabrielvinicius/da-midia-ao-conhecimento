"""Pydantic schemas used across media processing tasks and services."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MediaTaskPayload(BaseModel):
    """Common payload data shared across media processing tasks."""

    media_id: UUID
    storage_provider: str = Field(default="local", min_length=1)
    file_size_bytes: Optional[int] = Field(default=None, ge=0)


class TranscriptionTaskPayload(MediaTaskPayload):
    """Payload specific for transcription tasks."""

    transcription_provider: str = Field(default="default", min_length=1)
    language: str = Field(default="auto", min_length=2, max_length=10)
    summarization_provider: Optional[str] = Field(default=None)
    sentiment_provider: Optional[str] = Field(default=None)
    topic_modeling_provider: Optional[str] = Field(default=None)
    correlation_id: Optional[str] = None


class VideoTaskPayload(MediaTaskPayload):
    """Payload specific for video processing tasks."""
    pass


__all__ = [
    "MediaTaskPayload",
    "TranscriptionTaskPayload",
    "VideoTaskPayload",
]