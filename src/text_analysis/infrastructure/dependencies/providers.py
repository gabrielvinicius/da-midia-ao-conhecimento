"""Provider factories for text_analysis bounded context."""
from __future__ import annotations

from src.text_analysis.application.config import AnalysisConfig
from src.shared.infrastructure.messaging.event_bus import SupportsEventBus
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


def get_embedding_adapter(config: AnalysisConfig):
    return SentenceTransformerEmbeddingAdapter(config.embedding_model)


def get_topic_modeling_adapter(config: AnalysisConfig):
    # Se topic_model for "tfidf" usar fallback leve; caso contrário, BERTopic
    if str(config.topic_model).lower() == "tfidf":
        return TFIDFTopicModelingAdapter()
    return BERTopicAdapter(
        config.topic_model,
        use_transformer_representation=config.use_transformer_topic_representation,
        transformer_model_name=config.transformer_representation_model,
    )


def get_text_generation_adapter(config: AnalysisConfig):
    model_cfg = str(config.llm_model)
    # Roteamento declarativo
    # normaliza aliases amigáveis -> rota declarada
    if model_cfg in TEXT_GEN_ROUTING:
        model_cfg = TEXT_GEN_ROUTING[model_cfg]

    # Caminhos simples:
    # - "hf:..." -> transformers gen (modelo arbitrário)
    # - "llama3..." -> adapter dedicado (continua suportando antigo hf-llama3)
    if model_cfg.startswith("hf-llama3") or model_cfg.startswith("hf:llama3") or model_cfg.startswith("llama3"):
        return Llama3TransformersTextGenerationAdapter()
    if model_cfg.startswith("hf:"):
        name = model_cfg.replace("hf:", "", 1) or "facebook/bart-large-cnn"
        model_name = resolve_textgen_target(name)
        if not validate_textgen_name(f"hf:{name}"):
            raise ValueError(f"Provider de text_generation não suportado: {model_cfg}")
        return TransformersTextGenerationAdapter(model_name=model_name)
    if not validate_textgen_name(model_cfg):
        raise ValueError(f"Provider de text_generation não suportado: {model_cfg}")
    return OllamaTextGenerationAdapter(config.llm_model)


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
