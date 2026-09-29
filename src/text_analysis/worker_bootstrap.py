"""Bootstrap lightweight for text_analysis worker processes."""
from __future__ import annotations

from types import SimpleNamespace
from typing import Any, Optional

from src.text_analysis.application import (
    AnalysisConfig,
    NoOpTextAnalysisMetrics,
    TextAnalysisService,
)
from src.text_analysis.application.ports import TranscriptionQueryPort
from src.text_analysis.application.services.text_analysis_read_service import (
    TextAnalysisReadService,
)
from src.text_analysis.config.settings import text_analysis_settings
from src.text_analysis.infrastructure.dependencies.providers import get_event_bus
from src.text_analysis.infrastructure.metrics.prometheus_metrics import (
    PrometheusTextAnalysisMetrics,
)
from src.text_analysis.infrastructure.repositories.inmemory_analysis_repository import (
    InMemoryAnalysisRepository,
)


def build_metrics():
    try:
        import prometheus_client  # noqa: F401
        return PrometheusTextAnalysisMetrics()
    except Exception:
        return NoOpTextAnalysisMetrics()


def build_text_analysis_service(
    *,
    repository,
    event_bus,
    transcription_queries: TranscriptionQueryPort,
):
    from src.text_analysis.infrastructure.dependencies.pipeline_factory import (
        build_analysis_pipeline,
    )
    from src.text_analysis.infrastructure.repositories.feedback_repository import FeedbackRepository

    config = AnalysisConfig()
    # O repositório SQLAlchemy expõe a sessão usada pelos demais repositórios.
    session = getattr(repository, "session", None)
    pipeline = build_analysis_pipeline(config, session).pipeline
    feedback_repo = FeedbackRepository(session)

    metrics = build_metrics()

    service = TextAnalysisService(
        repository=repository,
        pipeline=pipeline,
        feedback_repo=feedback_repo,
        config=config,
        metrics=metrics,
        event_bus=get_event_bus(event_bus),
        transcription_queries=transcription_queries,
        text_analysis_read_service=TextAnalysisReadService(repository=repository),
        settings=text_analysis_settings,
    )
    return SimpleNamespace(service=service, repository=repository, config=config)


def build_repository(session: Any | None = None):
    if session is None:
        return InMemoryAnalysisRepository()
    from src.text_analysis.infrastructure.repositories.sqlalchemy_analysis_repository import (  # noqa: WPS433
        SqlAlchemyAnalysisRepository,
    )

    return SqlAlchemyAnalysisRepository(session)


__all__ = ["build_text_analysis_service", "build_repository"]
