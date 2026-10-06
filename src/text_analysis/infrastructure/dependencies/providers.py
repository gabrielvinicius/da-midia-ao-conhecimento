"""Provider factories for text_analysis bounded context."""
from __future__ import annotations

import structlog

from src.shared.infrastructure.model_cache import model_cache


from src.text_analysis.application.config import AnalysisConfig
from src.text_analysis.infrastructure.adapters import (
    chunking_simple_adapter,
    embeddings_sentence_transformers_adapter,
    sentiment_transformers_adapter,
    text_generation_ollama_adapter,
    topic_modeling_bertopic_adapter,
    topic_modeling_tfidf_adapter,
)

SimpleChunker = chunking_simple_adapter.SimpleChunker
SentenceTransformerEmbeddingAdapter = (
    embeddings_sentence_transformers_adapter.SentenceTransformerEmbeddingAdapter
)
TransformersSentimentAdapter = (
    sentiment_transformers_adapter.TransformersSentimentAdapter
)
OllamaTextGenerationAdapter = (
    text_generation_ollama_adapter.OllamaTextGenerationAdapter
)
BERTopicAdapter = topic_modeling_bertopic_adapter.BERTopicAdapter
TFIDFTopicModelingAdapter = topic_modeling_tfidf_adapter.TFIDFTopicModelingAdapter


def get_sentiment_adapter(config: AnalysisConfig):
    return TransformersSentimentAdapter(config.sentiment_model)



logger = structlog.get_logger(__name__)

def get_embedding_adapter(config: AnalysisConfig):
    return model_cache.get_or_create(
        ("embeddings", config.embedding_model),
        lambda: SentenceTransformerEmbeddingAdapter(config.embedding_model),
    )


def get_topic_modeling_adapter(config: AnalysisConfig):
    # Se topic_model for "tfidf" usar fallback leve; caso contrário, BERTopic
    if str(config.topic_model).lower() == "tfidf":
        return TFIDFTopicModelingAdapter()
    
    # Try to reuse the embedding model instance from the cached embedding adapter
    # to save VRAM (avoid loading SentenceTransformer twice).
    embedding_model_inst = None
    embeddings = model_cache.peek(("embeddings", config.embedding_model))
    if embeddings:
        try:
            if hasattr(embeddings, "get_model_instance"):
                embedding_model_inst = embeddings.get_model_instance()
        except Exception as exc:  # sem reaproveitar, o BERTopic carrega o próprio modelo
            logger.warning("topic_modeling.embedding_reuse_failed", error=str(exc))

    return BERTopicAdapter(
        config.topic_model,
        embedding_model_name=config.embedding_model,
        embedding_model_inst=embedding_model_inst, # Inject shared instance
    )


def get_text_generation_adapter(config: AnalysisConfig):
    # Nome do modelo servido pelo Ollama (ex.: "qwen3.5:9b").
    model = str(config.llm_model).removeprefix("ollama:")
    return model_cache.get_or_create(("text_generation", model), lambda: _build_text_generation_adapter(model))


def _build_text_generation_adapter(model: str):
    from src.shared.infrastructure.config.settings import settings

    return OllamaTextGenerationAdapter(
        model=model,
        host=settings.ollama_host,
        timeout=settings.llm_timeout_seconds,
        fallback_model=settings.llm_fallback_model,
        context_tokens=settings.llm_context_tokens,
    )


def get_chunker_adapter(_: AnalysisConfig):
    return SimpleChunker()


__all__ = [
    "get_sentiment_adapter",
    "get_embedding_adapter",
    "get_topic_modeling_adapter",
    "get_text_generation_adapter",
    "get_chunker_adapter",
]


def build_analysis_config(**overrides):
    """Configuração da análise a partir das configurações do ambiente."""
    from src.shared.infrastructure.config.settings import settings
    from src.text_analysis.application.config import AnalysisConfig

    from src.text_analysis.application.config import OPTIONAL_FACTORS

    factors = {f.strip().lower() for f in settings.analysis_factors.split(",") if f.strip()}
    unknown = factors - OPTIONAL_FACTORS
    if unknown:
        raise ValueError(f"ANALYSIS_FACTORS desconhecidos: {sorted(unknown)}; use {sorted(OPTIONAL_FACTORS)}")
    return AnalysisConfig(**{"llm_model": settings.llm_model, "factors": frozenset(factors), **overrides})


def runtime_diagnostics() -> dict:
    """Dispositivo e precisão em uso, registrados em cada análise."""
    from src.shared.infrastructure.config.settings import settings

    return {"hardware_target": settings.resolved_device, "compute_type": settings.ai_compute_type}
