"""Bootstrap and binding helpers for the text_analysis module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import FastAPI

from .application import (
    TextAnalysisService,
    AnalysisConfig,
    AnalyzeTextCommandHandler,
    GetAnalysisQueryHandler,
    ListTopicsQueryHandler,
    NoOpTextAnalysisMetrics,
)
from .infrastructure.metrics import PrometheusTextAnalysisMetrics
from src.providers.domain.interfaces import IProviderRegistry, ProviderCapability, ProviderStatus, ProviderType
from src.providers.domain.provider import Provider
from .infrastructure import (
    BERTopicAdapter,
    InMemoryAnalysisRepository,
    OllamaTextGenerationAdapter,
    SentenceTransformerEmbeddingAdapter,
    SimpleChunker,
    TransformersSentimentAdapter,
)
from .infrastructure.metrics import PrometheusTextAnalysisMetrics


def _prom_available() -> bool:
    try:
        import prometheus_client  # noqa: F401
        return True
    except Exception:
        return False


@dataclass
class TextAnalysisModule:
    service: TextAnalysisService
    analyze_handler: AnalyzeTextCommandHandler
    get_handler: GetAnalysisQueryHandler
    list_topics_handler: ListTopicsQueryHandler
    repository: InMemoryAnalysisRepository
    config: AnalysisConfig


async def build_text_analysis_module(
    session: Any,
    provider_registry: IProviderRegistry | None = None,
    repository: Any | None = None,
    event_bus: Any | None = None,
    **_kwargs: Any,
) -> TextAnalysisModule:
    _seed_text_analysis_providers(provider_registry)
    if repository is not None:
        repo = repository
    else:
        from .infrastructure.repository_sqlalchemy import SqlAlchemyAnalysisRepository

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

    analyze_handler = AnalyzeTextCommandHandler(
        sentiment_service=sentiment,
        embedding_service=embeddings,
        topic_modeling=topic_modeling,
        text_generation=text_generation,
        chunker=chunker,
        repository=repo,
        config=config,
        event_bus=event_bus,
    )
    get_handler = GetAnalysisQueryHandler(repo)
    list_topics_handler = ListTopicsQueryHandler(repo)

    metrics = PrometheusTextAnalysisMetrics() if _prom_available() else NoOpTextAnalysisMetrics()

    service = TextAnalysisService(
        provider_registry=provider_registry,
        analyze_handler=analyze_handler,
        get_handler=get_handler,
        list_topics_handler=list_topics_handler,
        metrics=metrics,
    )

    return TextAnalysisModule(
        service=service,
        analyze_handler=analyze_handler,
        get_handler=get_handler,
        list_topics_handler=list_topics_handler,
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
