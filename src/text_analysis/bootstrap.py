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
from .application.services.knowledge_base_service import KnowledgeBaseService
from .application.pipeline.base import AnalysisPipeline
from .application.pipeline.steps import (
    ChunkingStep,
    SentimentStep,
    TopicModelingStep,
    SummarizationStep,
    KnowledgeIndexingStep,
    VisualInsightStep,
    SynthesisStep,
)
from .infrastructure.repositories.vector_repository import VectorRepository
from .infrastructure.repositories.feedback_repository import FeedbackRepository
from src.media_processing.infrastructure.adapters.visual.moondream_adapter import MoondreamVisualAdapter
from src.media_processing.infrastructure.adapters.video.ffmpeg_frame_extractor import FFmpegFrameExtractor
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.shared.infrastructure.monitoring.hardware_advisor import HardwareAdvisor
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
from .infrastructure.dependencies import registry as ta_registry
from .infrastructure.dependencies.registry import needs_health_refresh, update_health_timestamp
from src.shared.infrastructure.observability.metrics.prometheus_metrics import SharedPrometheusMetrics

try:
    import httpx  # noqa: F401
except Exception:  # pragma: no cover
    httpx = None  # type: ignore


def _prom_available() -> bool:
    try:
        import prometheus_client  # noqa: F401
        return True
    except Exception:
        return False


@dataclass
class TextAnalysisModule:
    service: TextAnalysisService
    repository: Any
    config: AnalysisConfig
    knowledge_service: KnowledgeBaseService


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
            raise RuntimeError("TextAnalysis requires a database session for persistence")

        repo = SqlAlchemyAnalysisRepository(session)
    
    config = AnalysisConfig()

    # Provide a default transcription query adapter if none supplied
    if transcription_queries is None:
        from src.media_processing.infrastructure.dependencies.transcription_query_adapter import (
            TranscriptionQueryAdapter,
        )
        from src.media_processing.infrastructure.repositories.transcription_repository import (
            TranscriptionRepository,
        )
        from src.media_management.infrastructure.repositories.media_repository import (
            MediaRepository,
        )
        transcription_queries = TranscriptionQueryAdapter(
            repo=TranscriptionRepository(session),
            media_repo=MediaRepository(session)
        )

    # Normalizar acesso de leitura via serviço dedicado
    transcription_queries = TranscriptionReadService(transcription_queries)

    _update_registry_availability()

    # Adapters for Pipeline Steps
    sentiment_adapter = get_sentiment_adapter(config)
    embedding_adapter = get_embedding_adapter(config)
    topic_adapter = get_topic_modeling_adapter(config)
    gen_adapter = get_text_generation_adapter(config)
    chunker_adapter = get_chunker_adapter(config)

    # --- Build Pipeline ---
    advisor = HardwareAdvisor()
    vector_repo = VectorRepository(session)
    feedback_repo = FeedbackRepository(session)
    visual_adapter = MoondreamVisualAdapter()
    frame_extractor = FFmpegFrameExtractor()
    storage_factory = StorageServiceFactory()
    
    pipeline = AnalysisPipeline(steps=[
        ChunkingStep(chunker_adapter, size=config.chunk_size, overlap=config.chunk_overlap),
        SentimentStep(sentiment_adapter, language=config.language),
        TopicModelingStep(topic_adapter, embedding_adapter, language=config.language),
        KnowledgeIndexingStep(vector_repo),
        VisualInsightStep(visual_adapter, frame_extractor, storage_factory), # Level 7.0 Ready
        SummarizationStep(gen_adapter, language=config.language, advisor=advisor),
        SynthesisStep(gen_adapter, language=config.language), # NEW: Level 8.3 Synthesis
    ])

    metrics = (
        PrometheusTextAnalysisMetrics()
        if _prom_available()
        else NoOpTextAnalysisMetrics()
    )

    service = TextAnalysisService(
        repository=repo,
        pipeline=pipeline, # Injected Pipeline
        feedback_repo=feedback_repo, # NEW
        config=config,
        metrics=metrics,
        event_bus=event_bus,
        transcription_queries=transcription_queries,
        text_analysis_read_service=TextAnalysisReadService(repository=repo),
        settings=text_analysis_settings,
    )

    knowledge_service = KnowledgeBaseService(
        vector_repo=vector_repo,
        embedding_service=embedding_adapter
    )

    if event_bus:
        handler = build_text_content_ready_handler(service)
        event_bus.subscribe(TextContentReady, handler)

    return TextAnalysisModule(
        service=service,
        repository=repo,
        config=config,
        knowledge_service=knowledge_service
    )


def bind_text_analysis_module(app: FastAPI, module: TextAnalysisModule) -> None:
    """Register dependency overrides for text analysis.
    Uses dynamic resolution to ensure fresh sessions per request.
    """
    from fastapi import Depends
    from src.shared.infrastructure.database.db import get_db
    from .api.dependencies import get_text_analysis_service, get_knowledge_service

    async def resolve_service(session: AsyncSession = Depends(get_db)):
        # Re-build the module logic using the current request's session
        # This is the safest way to avoid 'session provisioning a new connection' errors
        m = await build_text_analysis_module(session=session)
        return m.service

    async def resolve_knowledge(session: AsyncSession = Depends(get_db)):
        m = await build_text_analysis_module(session=session)
        return m.knowledge_service

    app.dependency_overrides[get_text_analysis_service] = resolve_service
    app.dependency_overrides[get_knowledge_service] = resolve_knowledge


def _check_module_available(module_name: str) -> bool:
    """Helper to check if a heavy module is available without polluting sys.modules."""
    import importlib.util
    return importlib.util.find_spec(module_name) is not None


def _update_registry_availability() -> None:
    """Marca disponibilidade no registry sem carregar modelos pesados."""
    if not needs_health_refresh():
        return

    metrics = SharedPrometheusMetrics().get_provider_health_checks_total()

    # Transformers (HF)
    hf_available = _check_module_available("transformers")

    for entry in ta_registry.TEXT_GEN_PROVIDERS:
        if entry.name.startswith("hf:"):
            entry.available = hf_available
            metrics.labels(provider_type="textgen_hf", status="up" if hf_available else "down").inc()

    # Ollama: ping /api/tags com timeout curto
    ollama_ok = False
    if httpx:
        try:  # pragma: no cover - ambiente externo
            with httpx.Client(timeout=1.5) as client:
                resp = client.get("http://localhost:11434/api/tags")
                resp.raise_for_status()
                ollama_ok = True
        except Exception:
            ollama_ok = False
    for entry in ta_registry.TEXT_GEN_PROVIDERS:
        if entry.name.startswith("ollama:"):
            entry.available = ollama_ok
            metrics.labels(provider_type="textgen_ollama", status="up" if ollama_ok else "down").inc()

    # Topic modeling
    bertopic_ok = _check_module_available("bertopic")
    for entry in ta_registry.TOPIC_PROVIDERS:
        if entry.name == "bertopic":
            entry.available = bertopic_ok
            metrics.labels(provider_type="topic_bertopic", status="up" if bertopic_ok else "down").inc()

    # TF-IDF deps
    tfidf_ok = _check_module_available("sklearn") and _check_module_available("numpy")
    for entry in ta_registry.TOPIC_PROVIDERS:
        if entry.name == "tfidf":
            entry.available = tfidf_ok
            metrics.labels(provider_type="topic_tfidf", status="up" if tfidf_ok else "down").inc()

    update_health_timestamp()