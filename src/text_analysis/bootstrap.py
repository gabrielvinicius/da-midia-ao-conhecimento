"""Bootstrap and binding helpers for the text_analysis module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from fastapi import FastAPI

from src.shared.domain.events import TextContentReady

from .application import (
    AnalysisConfig,
    NoOpTextAnalysisMetrics,
    TextAnalysisService,
)
from .application.event_handlers import build_text_content_ready_handler
from .application.ports import TranscriptionQueryPort
from .application.services.text_analysis_read_service import TextAnalysisReadService
from src.media_processing.application.services.transcription_read_service import (
    TranscriptionReadService,
)
from .config.settings import text_analysis_settings
from .infrastructure.dependencies.providers import (
    get_chunker_adapter,
    get_embedding_adapter,
    get_sentiment_adapter,
    get_text_generation_adapter,
    get_topic_modeling_adapter,
)
from .infrastructure.metrics.prometheus_metrics import PrometheusTextAnalysisMetrics
from .infrastructure.repositories.inmemory_analysis_repository import (
    InMemoryAnalysisRepository,
)


def _prom_available() -> bool:
    try:
        import prometheus_client  # noqa: F401
        return True
    except Exception:
        return False


@dataclass
class TextAnalysisModule:
    service: TextAnalysisService
    repository: InMemoryAnalysisRepository
    config: AnalysisConfig


async def build_text_analysis_module(
    session: Any,
    repository: Any | None = None,
    event_bus: Any | None = None,
    transcription_queries: Optional[TranscriptionQueryPort] = None,
    **_kwargs: Any,
) -> TextAnalysisModule:
    if repository is not None:
        repo = repository
    else:
        from .infrastructure.repositories.sqlalchemy_analysis_repository import (
            SqlAlchemyAnalysisRepository,
        )

        if session is None:
            raise RuntimeError(
                "TextAnalysis requires a database session for persistence"
            )

        repo = SqlAlchemyAnalysisRepository(session)
    config = AnalysisConfig()

    # Provide a default transcription query adapter if none supplied
    if transcription_queries is None:
        if session is None:
            raise RuntimeError(
                "TextAnalysis requires transcription_queries "
                "or a session to build default adapter"
            )
        try:
            from src.media_processing.infrastructure.dependencies import (
                transcription_query_adapter,
            )
            from src.media_processing.infrastructure.repositories import (
                transcription_repository,
            )

            transcription_queries = (
                transcription_query_adapter.TranscriptionQueryAdapter(  # type: ignore[attr-defined]
                    transcription_repository.TranscriptionRepository(session)  # type: ignore[attr-defined]
                )
            )
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(
                "Failed to build default transcription query adapter"
            ) from exc

    # Normalizar acesso de leitura via serviço dedicado
    transcription_queries = TranscriptionReadService(transcription_queries)

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

    service = TextAnalysisService(
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

    if event_bus:
        handler = build_text_content_ready_handler(service)
        event_bus.subscribe(TextContentReady, handler)

    return TextAnalysisModule(
        service=service,
        repository=repo,
        config=config,
    )


def bind_text_analysis_module(app: FastAPI, module: TextAnalysisModule) -> None:
    from .api.dependencies import get_text_analysis_service

    app.dependency_overrides[get_text_analysis_service] = lambda: module.service


def _seed_text_analysis_providers(_: Any | None) -> None:
    """No-op: provider registry removed in per-context ownership model."""
