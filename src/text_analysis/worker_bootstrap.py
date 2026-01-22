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
from src.text_analysis.infrastructure.dependencies.providers import (
    get_chunker_adapter,
    get_embedding_adapter,
    get_event_bus,
    get_sentiment_adapter,
    get_text_generation_adapter,
    get_topic_modeling_adapter,
)
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
    from src.text_analysis.application.pipeline.base import AnalysisPipeline
    from src.text_analysis.application.pipeline.steps import (
        ChunkingStep,
        SentimentStep,
        TopicModelingStep,
        SummarizationStep,
        KnowledgeIndexingStep,
        VisualInsightStep,
        SynthesisStep,
    )
    from src.text_analysis.infrastructure.repositories.vector_repository import VectorRepository
    from src.text_analysis.infrastructure.repositories.feedback_repository import FeedbackRepository
    from src.shared.infrastructure.monitoring.hardware_advisor import HardwareAdvisor
    from src.media_processing.infrastructure.adapters.visual.moondream_adapter import MoondreamVisualAdapter
    from src.media_processing.infrastructure.adapters.video.ffmpeg_frame_extractor import FFmpegFrameExtractor
    from src.storage.infrastructure.dependencies import StorageServiceFactory

    config = AnalysisConfig()
    
    # Adapters
    sentiment_adapter = get_sentiment_adapter(config)
    embedding_adapter = get_embedding_adapter(config)
    topic_adapter = get_topic_modeling_adapter(config)
    gen_adapter = get_text_generation_adapter(config)
    chunker_adapter = get_chunker_adapter(config)

    # Infrastructure
    # Note: we need the session to build repos. 
    # repository is already a SqlAlchemyAnalysisRepository (which has .session)
    session = getattr(repository, "session", None)
    
    advisor = HardwareAdvisor()
    vector_repo = VectorRepository(session)
    feedback_repo = FeedbackRepository(session)
    visual_adapter = MoondreamVisualAdapter()
    frame_extractor = FFmpegFrameExtractor()
    storage_factory = StorageServiceFactory()

    # Build Pipeline
    pipeline = AnalysisPipeline(steps=[
        ChunkingStep(chunker_adapter, size=config.chunk_size, overlap=config.chunk_overlap),
        SentimentStep(sentiment_adapter, language=config.language),
        TopicModelingStep(topic_adapter, embedding_adapter, language=config.language),
        KnowledgeIndexingStep(vector_repo),
        VisualInsightStep(visual_adapter, frame_extractor, storage_factory),
        SummarizationStep(gen_adapter, language=config.language, advisor=advisor, turbo_mode=config.turbo_mode),
        SynthesisStep(gen_adapter, language=config.language),
    ])

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
