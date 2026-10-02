from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict

class TextAnalysisSettings(BaseSettings):
    """Text analysis bounded-context settings."""

    summarization_providers_allowed: list[str] = ["ollama", "mock"]
    sentiment_providers_allowed: list[str] = ["transformers", "mock"]
    embedding_providers_allowed: list[str] = ["sentence_transformers", "mock"]
    topic_providers_allowed: list[str] = ["bertopic", "mock"]
    generation_providers_allowed: list[str] = ["ollama", "mock"]

    model_config = SettingsConfigDict(
        env_prefix="TEXT_",
        case_sensitive=False,
        extra="ignore",
    )


text_analysis_settings = TextAnalysisSettings()


__all__ = ["TextAnalysisSettings", "text_analysis_settings"]
