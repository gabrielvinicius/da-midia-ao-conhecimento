"""Esquemas da API da análise."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    """Pedido de nova análise de uma mídia; o texto vem da sua transcrição.

    Antes aceitava texto, segmentos e tamanho dos trechos, que nada usava.
    """

    media_id: UUID = Field(..., description="Mídia a analisar de novo.")


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
    summary: str | None = None


class ReviewProgressResponse(BaseModel):
    box: int = Field(..., description="Caixa de 1 a 5; a partir da 4, dominada.")
    correct_count: int
    wrong_count: int
    last_answered_at: Optional[datetime] = None
    due_at: Optional[datetime] = None


class StudyQuestionResponse(BaseModel):
    question: str
    answer: str
    start: Optional[float] = None
    progress: Optional[ReviewProgressResponse] = Field(None, description="Vazio: nunca respondida.")
    due: bool = Field(True, description="Para revisar agora.")


class ReviewAnswerRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    correct: bool


class NotebookEntryResponse(BaseModel):
    media_id: Optional[UUID] = None
    analysis_id: UUID
    summary: str
    genre: Optional[str] = None
    topics: List[str]
    chapters: int
    questions: int


class TopicOccurrenceResponse(BaseModel):
    media_id: Optional[UUID] = None
    analysis_id: UUID
    title: str
    keywords: List[str]
    snippet: Optional[str] = None
    start: Optional[float] = None


class TopicGroupResponse(BaseModel):
    title: str
    media_count: int
    occurrences: List[TopicOccurrenceResponse]


class StudyDeckEntryResponse(BaseModel):
    media_id: Optional[UUID] = None
    analysis_id: UUID
    questions: List[StudyQuestionResponse]
