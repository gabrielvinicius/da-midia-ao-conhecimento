"""Pydantic schemas for text analysis API."""

from __future__ import annotations

from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, root_validator


class Segment(BaseModel):
    start: Optional[float] = None
    end: Optional[float] = None
    text: str


class AnalyzeRequest(BaseModel):
    text: Optional[str] = None
    media_id: Optional[UUID] = None
    transcription_id: Optional[UUID] = None
    segments: Optional[List[Segment]] = None
    language: Optional[str] = Field(default="pt")
    provider: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    use_transformer_topic_representation: Optional[bool] = None
    transformer_representation_model: Optional[str] = None
    llm_model: Optional[str] = None

    @root_validator(pre=True)
    def trim_text(cls, values: dict[str, Any]) -> dict[str, Any]:
        if "text" in values and isinstance(values["text"], str):
            values["text"] = values["text"].strip()
        return values

    @root_validator
    def ensure_source_present(cls, values: dict[str, Any]) -> dict[str, Any]:
        has_text = bool(values.get("text"))
        has_ids = bool(values.get("media_id") or values.get("transcription_id"))
        if not has_text and not has_ids:
            raise ValueError("Informe texto ou um media_id/transcription_id para análise")
        return values


class AnalyzeResponse(BaseModel):
    analysis_id: str
    document_id: str
    overall_sentiment: str
    sentiment_items: list[dict]
    topics: list[dict]
    diagnostics: dict
    media_id: str | None = None
    transcription_id: str | None = None
    provider: str | None = None
    user_id: str | None = None
