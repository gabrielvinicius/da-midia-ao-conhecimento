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
from src.text_analysis.application.services.analysis_request_service import (
    AnalysisRequestService,
)
from src.text_analysis.application.services.analysis_review_service import (
    AnalysisReviewService,
)
from src.text_analysis.application.services.knowledge_base_service import (
    KnowledgeBaseService,
)
from src.text_analysis.application.services.text_analysis_read_service import (
    TextAnalysisReadService,
)
from src.text_analysis.infrastructure.adapters.celery_analysis_queue import CeleryAnalysisQueue
from src.text_analysis.infrastructure.dependencies.pipeline_factory import (
    build_analysis_pipeline,
)
from src.text_analysis.infrastructure.dependencies.providers import (
    build_analysis_config,
    get_embedding_adapter,
    get_reranker_adapter,
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
    """Execução da análise (worker): monta o pipeline e os modelos."""
    config = build_analysis_config()
    return TextAnalysisService(
        repository=repository or SqlAlchemyAnalysisRepository(session),
        pipeline=build_analysis_pipeline(config, session).pipeline,
        config=config,
        metrics=_metrics(),
        event_bus=event_bus,
        transcription_queries=transcription_queries or build_transcription_queries(session),
        stats_recorder=_stats_recorder(session),
        runtime_diagnostics=runtime_diagnostics(),
    )


def build_analysis_read_service(session, *, repository: Any = None) -> TextAnalysisReadService:
    return TextAnalysisReadService(repository=repository or SqlAlchemyAnalysisRepository(session))


def build_analysis_review_service(session, *, repository: Any = None) -> AnalysisReviewService:
    return AnalysisReviewService(
        repository=repository or SqlAlchemyAnalysisRepository(session),
        feedback_repo=FeedbackRepository(session),
    )


def build_analysis_request_service(
    session, *, transcription_queries: Optional[TranscriptionQueryPort] = None
) -> AnalysisRequestService:
    """Pedido de análise pela API: vai para a fila, sem pipeline nem modelos."""
    return AnalysisRequestService(
        sources=transcription_queries or build_transcription_queries(session),
        queue=CeleryAnalysisQueue(),
    )


def build_knowledge_service(session) -> KnowledgeBaseService:
    """Busca semântica: vetor da pergunta, trechos do próprio usuário e, se
    configurado, o reranqueador que os ordena."""
    from src.shared.infrastructure.config.settings import settings

    return KnowledgeBaseService(
        vector_repo=VectorRepository(session),
        embedding_service=get_embedding_adapter(build_analysis_config()),
        reranker=get_reranker_adapter(settings.search_reranker_model),
        analyses=SqlAlchemyAnalysisRepository(session),
    )


__all__ = [
    "build_analysis_read_service",
    "build_analysis_request_service",
    "build_analysis_review_service",
    "build_knowledge_service",
    "build_text_analysis_service",
    "build_transcription_queries",
]
