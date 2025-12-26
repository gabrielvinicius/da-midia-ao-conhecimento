"""Configuration objects for application layer."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class AnalysisConfig:
    language: str = "pt"
    chunk_size: int = 512
    chunk_overlap: int = 64
    max_chunks: int = 200
    sentiment_model: str = "nlptown/bert-base-multilingual-uncased-sentiment"
    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    topic_model: str = "bertopic"  # use "tfidf" para fallback leve sem deps pesadas
    llm_model: str = "llama3.1:8b"
    use_transformer_topic_representation: bool = False
    transformer_representation_model: str = "llama3.1:8b"
