"""Pydantic schemas for text analysis background payloads."""
from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from src.media_processing.application.schemas import MediaTaskPayload


class TextProcessPayload(BaseModel):
    """Payload for text processing tasks."""

    media_id: UUID
    text_content: str = Field(min_length=1)
    processing_type: str = Field(min_length=1)
    options: Optional[Dict[str, Any]] = None


class TextExtractionPayload(MediaTaskPayload):
    """Payload for text extraction tasks."""

    extraction_method: str = Field(default="basic", min_length=1)


class SummarizationTaskPayload(BaseModel):
    """Payload for summarization tasks executed via Celery."""

    transcription_id: UUID
    media_id: Optional[UUID] = None
    text_content: str = Field(min_length=1)
    provider: str = Field(default="builtin", min_length=1)
    options: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def _ensure_ids(self) -> "SummarizationTaskPayload":
        if self.transcription_id is None:
            raise ValueError("transcription_id is required for summarization tasks")
        return self


class SentimentTaskPayload(BaseModel):
    """Payload for sentiment analysis tasks."""

    transcription_id: UUID
    text: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    model: Optional[str] = Field(default=None, min_length=1)
    media_id: Optional[UUID] = None
    language: Optional[str] = Field(default=None, min_length=2, max_length=10)


class TopicModelingTaskPayload(BaseModel):
    """Payload for topic modeling tasks."""

    transcription_id: UUID
    text_content: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    language: str = Field(min_length=2, max_length=32)
    options: Optional[Dict[str, Any]] = None


class TopicExtractionTaskPayload(BaseModel):
    """Payload for legacy topic extraction tasks awaiting consolidation."""

    media_id: UUID
    text_content: str = Field(min_length=1)
    provider: str = Field(default="sklearn_lda", min_length=1)


__all__ = [
    "TextProcessPayload",
    "TextExtractionPayload",
    "SummarizationTaskPayload",
    "SentimentTaskPayload",
    "TopicModelingTaskPayload",
    "TopicExtractionTaskPayload",
]
