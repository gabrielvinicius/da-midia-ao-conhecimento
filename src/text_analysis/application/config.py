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
    # Opções: "intfloat/multilingual-e5-large" (SOTA Multilingual)
    embedding_model: str = "intfloat/multilingual-e5-large"
    topic_model: str = "bertopic"  # use "tfidf" para fallback leve sem deps pesadas
    llm_model: str = "hf:Qwen/Qwen2.5-7B-Instruct"
    use_transformer_topic_representation: bool = True
    transformer_representation_model: str = "hf:Qwen/Qwen2.5-7B-Instruct"
    turbo_mode: bool = True  # Pula sumarização granular para one-shot synthesis
