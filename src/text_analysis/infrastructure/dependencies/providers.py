"""Provider factories for text_analysis bounded context."""
from __future__ import annotations

import structlog

from src.shared.infrastructure.model_cache import model_cache


from src.text_analysis.application.config import AnalysisConfig
from src.shared.application.event_bus import SupportsEventBus
from src.text_analysis.infrastructure.adapters import (
    chunking_simple_adapter,
    embeddings_sentence_transformers_adapter,
    sentiment_transformers_adapter,
    text_generation_ollama_adapter,
    text_generation_llama3_transformers_adapter,
    text_generation_transformers_adapter,
    topic_modeling_bertopic_adapter,
    topic_modeling_tfidf_adapter,
)
from src.text_analysis.infrastructure.dependencies.registry import (
    resolve_textgen_target,
    TEXT_GEN_ROUTING,
    validate_textgen_name,
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
TransformersTextGenerationAdapter = (
    text_generation_transformers_adapter.TransformersTextGenerationAdapter
)
Llama3TransformersTextGenerationAdapter = (
    text_generation_llama3_transformers_adapter.Llama3TransformersTextGenerationAdapter
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
        use_transformer_representation=config.use_transformer_topic_representation,
        transformer_model_name=config.transformer_representation_model,
        embedding_model_name=config.embedding_model,
        embedding_model_inst=embedding_model_inst, # Inject shared instance
    )


def get_text_generation_adapter(config: AnalysisConfig):
    model_cfg = str(config.llm_model)
    # Roteamento declarativo
    if model_cfg in TEXT_GEN_ROUTING:
        model_cfg = TEXT_GEN_ROUTING[model_cfg]
    return model_cache.get_or_create(
        ("text_generation", model_cfg), lambda: _build_text_generation_adapter(model_cfg)
    )


def _build_text_generation_adapter(model_cfg: str):
    if model_cfg.startswith(("hf-llama3", "hf:llama3")) or model_cfg == "llama3":
        adapter = Llama3TransformersTextGenerationAdapter()
    elif model_cfg.startswith("hf:"):
        if not validate_textgen_name(model_cfg):
            raise ValueError(f"Modelo de geração de texto desconhecido: {model_cfg}")
        name = model_cfg.replace("hf:", "", 1) or "facebook/bart-large-cnn"
        model_name = resolve_textgen_target(name)
        adapter = TransformersTextGenerationAdapter(model_name=model_name)
    else:
        from src.shared.infrastructure.config.settings import settings

        # Nome sem prefixo = modelo servido pelo Ollama (ex.: "qwen3.5:9b").
        model_cfg = model_cfg.removeprefix("ollama:")
        adapter = OllamaTextGenerationAdapter(
            model=model_cfg,
            host=settings.ollama_host,
            timeout=settings.llm_timeout_seconds,
            fallback_model=settings.llm_fallback_model,
            context_tokens=settings.llm_context_tokens,
        )
    return adapter


def get_chunker_adapter(_: AnalysisConfig):
    return SimpleChunker()


def get_event_bus(event_bus: SupportsEventBus | None = None) -> SupportsEventBus:
    """Retorna o event bus recebido do bootstrap; falha se não for fornecido."""
    if event_bus is None:
        raise RuntimeError(
            "TextAnalysis event bus não fornecido. Passe via bootstrap/tasks ou "
            "configure o worker para inicializar EVENT_BUS antes de executar as tasks."
        )
    return event_bus


__all__ = [
    "get_sentiment_adapter",
    "get_embedding_adapter",
    "get_topic_modeling_adapter",
    "get_text_generation_adapter",
    "get_chunker_adapter",
    "get_event_bus",
]


def build_analysis_config(**overrides):
    """Configuração da análise a partir das configurações do ambiente."""
    from src.shared.infrastructure.config.settings import settings
    from src.text_analysis.application.config import AnalysisConfig

    return AnalysisConfig(**{"llm_model": settings.llm_model, **overrides})


def runtime_diagnostics() -> dict:
    """Dispositivo e precisão em uso, registrados em cada análise."""
    from src.shared.infrastructure.config.settings import settings

    return {"hardware_target": settings.resolved_device, "compute_type": settings.ai_compute_type}
