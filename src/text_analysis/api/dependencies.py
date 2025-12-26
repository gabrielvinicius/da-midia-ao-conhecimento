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


def _prom_available() -> bool:
    try:
        import prometheus_client  # noqa: F401

        return True
    except Exception:
        return False


def get_text_analysis_service(
    request: Request,
    session: AsyncSession = Depends(get_db),
) -> TextAnalysisService:
    """Provider padrão (por request) do serviço de análise de texto."""

    event_bus = getattr(request.app.state, "event_bus", None)

    repo = SqlAlchemyAnalysisRepository(session)
    config = AnalysisConfig()

    transcription_repo = TranscriptionRepository(db=session)
    transcription_queries = TranscriptionReadService(
        TranscriptionQueryAdapter(transcription_repo)
    )

    sentiment = get_sentiment_adapter(config)
    embeddings = get_embedding_adapter(config)
    topic_modeling = get_topic_modeling_adapter(config)
    text_generation = get_text_generation_adapter(config)
    chunker = get_chunker_adapter(config)

    metrics = (
        PrometheusTextAnalysisMetrics()
        if _prom_available()
        else NoOpTextAnalysisMetrics()
    )

    return TextAnalysisService(
        sentiment_service=sentiment,
        embedding_service=embeddings,
        topic_modeling=topic_modeling,
        text_generation=text_generation,
        chunker=chunker,
        repository=repo,
        config=config,
        metrics=metrics,
        event_bus=event_bus,
        transcription_queries=transcription_queries,
        text_analysis_read_service=TextAnalysisReadService(repository=repo),
        settings=text_analysis_settings,
    )


__all__ = ["get_text_analysis_service", "AnalyzeRequest", "AnalyzeResponse"]
