"""Esquemas da API da análise."""

from __future__ import annotations

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
