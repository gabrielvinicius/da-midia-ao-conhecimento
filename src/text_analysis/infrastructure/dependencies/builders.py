"""Montagem dos serviços da análise: um único lugar para a API e os workers.

Antes, a API e o worker montavam o TextAnalysisService cada um à sua maneira;
na API, a consulta à transcrição era embrulhada num serviço sem os métodos
que a análise usa, e a falha só aparecia como aviso no log.
"""
from __future__ import annotations

from typing import Any, Optional

from src.shared.application.event_bus import SupportsEventBus
from src.text_analysis.application import NoOpTextAnalysisMetrics, TextAnalysisService
from src.text_analysis.application.ports import TranscriptionQueryPort
from src.text_analysis.application.services.knowledge_base_service import (
    KnowledgeBaseService,
)
from src.text_analysis.application.services.text_analysis_read_service import (
    TextAnalysisReadService,
)
from src.text_analysis.config.settings import text_analysis_settings
from src.text_analysis.infrastructure.dependencies.pipeline_factory import (
    build_analysis_pipeline,
)
from src.text_analysis.infrastructure.dependencies.providers import (
    build_analysis_config,
    get_embedding_adapter,
    runtime_diagnostics,
)
from src.text_analysis.infrastructure.repositories.feedback_repository import FeedbackRepository
from src.text_analysis.infrastructure.repositories.sqlalchemy_analysis_repository import (
    SqlAlchemyAnalysisRepository,
)
from src.text_analysis.infrastructure.repositories.vector_repository import VectorRepository


def build_transcription_queries(session) -> TranscriptionQueryPort:
    """Consulta à transcrição e à mídia, implementada pelo módulo de processamento."""
    from src.media_management.infrastructure.repositories.media_repository import (
        MediaRepository,
    )
    from src.media_processing.infrastructure.dependencies.transcription_query_adapter import (
        TranscriptionQueryAdapter,
    )
    from src.media_processing.infrastructure.repositories.transcription_repository import (
        TranscriptionRepository,
    )

    return TranscriptionQueryAdapter(TranscriptionRepository(session), MediaRepository(session))


def _metrics():
    try:
        import prometheus_client  # noqa: F401

        from src.text_analysis.infrastructure.metrics.prometheus_metrics import (
            PrometheusTextAnalysisMetrics,
        )

        return PrometheusTextAnalysisMetrics()
    except Exception:
        return NoOpTextAnalysisMetrics()


def _stats_recorder(session):
    if session is None:
        return None
    from src.shared.infrastructure.repositories.processing_stats_repository import (
        ProcessingStatsRepository,
    )

    return ProcessingStatsRepository(session)


def build_text_analysis_service(
    session,
    event_bus: Optional[SupportsEventBus],
    *,
    repository: Any = None,
    transcription_queries: Optional[TranscriptionQueryPort] = None,
) -> TextAnalysisService:
    config = build_analysis_config()
    repository = repository or SqlAlchemyAnalysisRepository(session)
    return TextAnalysisService(
        repository=repository,
        pipeline=build_analysis_pipeline(config, session).pipeline,
        feedback_repo=FeedbackRepository(session),
        config=config,
        metrics=_metrics(),
        event_bus=event_bus,
        transcription_queries=transcription_queries or build_transcription_queries(session),
        text_analysis_read_service=TextAnalysisReadService(repository=repository),
        settings=text_analysis_settings,
        stats_recorder=_stats_recorder(session),
        runtime_diagnostics=runtime_diagnostics(),
    )


def build_knowledge_service(session) -> KnowledgeBaseService:
    """Busca semântica: vetor da pergunta e trechos do próprio usuário."""
    return KnowledgeBaseService(
        vector_repo=VectorRepository(session),
        embedding_service=get_embedding_adapter(build_analysis_config()),
    )


__all__ = ["build_knowledge_service", "build_text_analysis_service", "build_transcription_queries"]
