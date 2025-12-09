"""Bootstrap and binding helpers for the text_analysis module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI

from .application import (
    TextAnalysisService,
    AnalysisConfig,
    NoOpTextAnalysisMetrics,
)
from .application.event_handlers import build_text_content_ready_handler
from .application.text_analysis_read_service import TextAnalysisReadService
from src.shared.domain.events import TextContentReady
from .infrastructure.adapters.topic_modeling_bertopic_adapter import BERTopicAdapter
from .infrastructure.repositories.inmemory_analysis_repository import InMemoryAnalysisRepository
from .infrastructure.adapters.text_generation_ollama_adapter import OllamaTextGenerationAdapter
from .infrastructure.adapters.embeddings_sentence_transformers_adapter import SentenceTransformerEmbeddingAdapter
from .infrastructure.adapters.chunking_simple_adapter import SimpleChunker
from .infrastructure.adapters.sentiment_transformers_adapter import TransformersSentimentAdapter
from .infrastructure.metrics.prometheus_metrics import PrometheusTextAnalysisMetrics


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
    provider_registry: IProviderRegistry | None = None,
    repository: Any | None = None,
    event_bus: Any | None = None,
    transcription_queries: Any | None = None,
    **_kwargs: Any,
) -> TextAnalysisModule:
    _seed_text_analysis_providers(provider_registry)
    if repository is not None:
        repo = repository
    else:
        from .infrastructure.repositories.sqlalchemy_analysis_repository import SqlAlchemyAnalysisRepository

        if session is None:
            raise RuntimeError("TextAnalysis requires a database session for persistence")

        repo = SqlAlchemyAnalysisRepository(session)
    config = AnalysisConfig()

    sentiment = TransformersSentimentAdapter(config.sentiment_model)
    embeddings = SentenceTransformerEmbeddingAdapter(config.embedding_model)
    topic_modeling = BERTopicAdapter(
        config.topic_model,
        use_transformer_representation=config.use_transformer_topic_representation,
        transformer_model_name=config.transformer_representation_model,
    )
    text_generation = OllamaTextGenerationAdapter(config.llm_model)
    chunker = SimpleChunker()

    metrics = PrometheusTextAnalysisMetrics() if _prom_available() else NoOpTextAnalysisMetrics()

    service = TextAnalysisService(
        sentiment_service=sentiment,
        embedding_service=embeddings,
        topic_modeling=topic_modeling,
        text_generation=text_generation,
        chunker=chunker,
        repository=repo,
        provider_registry=provider_registry,
        config=config,
        metrics=metrics,
        event_bus=event_bus,
        transcription_queries=transcription_queries,
        text_analysis_read_service=TextAnalysisReadService(repository=repo),
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


def _seed_text_analysis_providers(registry: IProviderRegistry | None) -> None:
    if registry is None:
        return
    providers = [
        Provider(
            name="transformers",
            provider_type=ProviderType.SENTIMENT_ANALYSIS,
            status=ProviderStatus.ACTIVE,
            capabilities=[ProviderCapability.BATCH_PROCESSING, ProviderCapability.MULTI_LANGUAGE],
        ),
        Provider(
            name="sentence_transformers",
            provider_type=ProviderType.EMBEDDING,
            status=ProviderStatus.ACTIVE,
            capabilities=[ProviderCapability.BATCH_PROCESSING, ProviderCapability.MULTI_LANGUAGE],
        ),
        Provider(
            name="bertopic",
            provider_type=ProviderType.TOPIC_MODELING,
            status=ProviderStatus.ACTIVE,
            capabilities=[ProviderCapability.BATCH_PROCESSING],
        ),
        Provider(
            name="ollama",
            provider_type=ProviderType.SUMMARIZATION,
            status=ProviderStatus.ACTIVE,
            capabilities=[ProviderCapability.BATCH_PROCESSING, ProviderCapability.MULTI_LANGUAGE, ProviderCapability.CUSTOM_MODELS],
        ),
    ]

    for provider in providers:
        try:
            registry.register_provider(provider)
        except Exception:
            continue