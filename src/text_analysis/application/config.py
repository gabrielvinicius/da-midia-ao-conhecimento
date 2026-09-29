"""Configuration objects for application layer."""

from __future__ import annotations

from dataclasses import dataclass, field


def _default_llm_model() -> str:
    from src.shared.infrastructure.config.settings import settings

    return settings.llm_model


@dataclass(slots=True)
class AnalysisConfig:
    language: str = "pt"
    chunk_size: int = 512
    chunk_overlap: int = 64
    max_chunks: int = 200
    sentiment_model: str = "cardiffnlp/twitter-xlm-roberta-base-sentiment"
    # multilingual-e5-small gera vetores de 384 dimensões, compatíveis com a
    # coluna knowledge_chunks.embedding (Vector(384)).
    embedding_model: str = "intfloat/multilingual-e5-small"
    topic_model: str = "bertopic"  # use "tfidf" para fallback leve sem deps pesadas
    # Nome de modelo Ollama (ex.: "qwen3.5:9b"); prefixo "hf:" usa Transformers.
    llm_model: str = field(default_factory=_default_llm_model)
    # Carregar um segundo LLM dentro do BERTopic não cabe em GPUs de 12 GB;
    # os títulos dos temas são gerados pelo LLM principal no TopicTitleStep.
    use_transformer_topic_representation: bool = False
    transformer_representation_model: str = "hf:Qwen/Qwen2.5-3B-Instruct"
    # Com turbo_mode, os resumos por tema são pulados e a síntese recebe o
    # material bruto (transcrição completa quando couber no contexto).
    turbo_mode: bool = True
    # Limite aproximado de caracteres da transcrição enviada integralmente ao LLM.
    max_full_transcript_chars: int = 60000
