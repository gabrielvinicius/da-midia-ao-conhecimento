"""FastAPI dependency helpers for text analysis."""

from __future__ import annotations

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.database.db import get_db
from src.media_processing.infrastructure.dependencies.transcription_query_adapter import (
    TranscriptionQueryAdapter,
)
from src.media_processing.infrastructure.repositories.transcription_repository import (
    TranscriptionRepository,
)
from src.media_processing.application.services.transcription_read_service import (
    TranscriptionReadService,
)

from ..application import AnalysisConfig, NoOpTextAnalysisMetrics, TextAnalysisService
from ..application.services.text_analysis_read_service import TextAnalysisReadService
from ..config.settings import text_analysis_settings
from ..infrastructure.dependencies.providers import (
    get_chunker_adapter,
    get_embedding_adapter,
    get_sentiment_adapter,
    get_text_generation_adapter,
    get_topic_modeling_adapter,
)
from ..infrastructure.metrics.prometheus_metrics import PrometheusTextAnalysisMetrics
from ..infrastructure.repositories.sqlalchemy_analysis_repository import (
    SqlAlchemyAnalysisRepository,
)
from .schemas import AnalyzeRequest, AnalyzeResponse
from ..application.services.knowledge_base_service import KnowledgeBaseService


def get_text_analysis_service() -> TextAnalysisService:
    """Returns the TextAnalysisService instance."""
    raise NotImplementedError("TextAnalysisService not configured.")


def get_knowledge_service() -> KnowledgeBaseService:
    """Returns the KnowledgeBaseService instance."""
    raise NotImplementedError("KnowledgeBaseService not configured.")


__all__ = ["get_text_analysis_service", "get_knowledge_service", "AnalyzeRequest", "AnalyzeResponse"]
