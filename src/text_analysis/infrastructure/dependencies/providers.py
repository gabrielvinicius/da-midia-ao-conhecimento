"""Provider factories for text_analysis bounded context."""
from __future__ import annotations

from src.text_analysis.application.config import AnalysisConfig
from src.shared.infrastructure.messaging.event_bus import SupportsEventBus
from src.text_analysis.infrastructure.adapters import (
    chunking_simple_adapter,
    embeddings_sentence_transformers_adapter,
    sentiment_transformers_adapter,
    text_generation_ollama_adapter,
    topic_modeling_bertopic_adapter,
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


def get_sentiment_adapter(config: AnalysisConfig):
    return TransformersSentimentAdapter(config.sentiment_model)


def get_embedding_adapter(config: AnalysisConfig):
    return SentenceTransformerEmbeddingAdapter(config.embedding_model)


def get_topic_modeling_adapter(config: AnalysisConfig):
    return BERTopicAdapter(
        config.topic_model,
        use_transformer_representation=config.use_transformer_topic_representation,
        transformer_model_name=config.transformer_representation_model,
    )


def get_text_generation_adapter(config: AnalysisConfig):
    return OllamaTextGenerationAdapter(config.llm_model)


def get_chunker_adapter(_: AnalysisConfig):
    return SimpleChunker()


def get_event_bus(event_bus: SupportsEventBus | None = None) -> SupportsEventBus:
    """Retorna o event bus recebido do bootstrap; falha se não for fornecido."""
    if event_bus is None:
        raise RuntimeError(
            "TextAnalysis event bus não fornecido. Passe via bootstrap/tasks."
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
