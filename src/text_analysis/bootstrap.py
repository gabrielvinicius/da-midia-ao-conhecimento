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
                "TextAnalysis requires transcription_queries or a DB session to "
                "build the default adapter (media_processing.TranscriptionRepository)."
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
                "Failed to build default transcription query adapter; "
                "inject transcription_queries explicitly in the bootstrap."
            ) from exc

    # Normalizar acesso de leitura via serviço dedicado
    transcription_queries = TranscriptionReadService(transcription_queries)

    _update_registry_availability()

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


def _update_registry_availability() -> None:
    """Marca disponibilidade no registry sem carregar modelos pesados."""
    if not needs_health_refresh():
        return

    metrics = SharedPrometheusMetrics().get_provider_health_checks_total()

    # Transformers (HF): verifica import leve
    try:
        import transformers  # noqa: F401
        hf_available = True
    except Exception:
        hf_available = False

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
    try:
        import bertopic  # noqa: F401
        bertopic_ok = True
    except Exception:
        bertopic_ok = False
    for entry in ta_registry.TOPIC_PROVIDERS:
        if entry.name == "bertopic":
            entry.available = bertopic_ok
            metrics.labels(provider_type="topic_bertopic", status="up" if bertopic_ok else "down").inc()

    # TF-IDF deps
    try:
        import sklearn  # noqa: F401
        import numpy  # noqa: F401
        tfidf_ok = True
    except Exception:
        tfidf_ok = False
    for entry in ta_registry.TOPIC_PROVIDERS:
        if entry.name == "tfidf":
            entry.available = tfidf_ok
            metrics.labels(provider_type="topic_tfidf", status="up" if tfidf_ok else "down").inc()

    update_health_timestamp()
