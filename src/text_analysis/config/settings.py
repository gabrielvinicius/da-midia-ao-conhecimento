from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class TextAnalysisSettings(BaseSettings):
    """Text analysis bounded-context settings."""

    summarization_providers_allowed: List[str] = ["ollama", "mock"]
    sentiment_providers_allowed: List[str] = ["transformers", "mock"]
    embedding_providers_allowed: List[str] = ["sentence_transformers", "mock"]
    topic_providers_allowed: List[str] = ["bertopic", "mock"]
    generation_providers_allowed: List[str] = ["ollama", "mock"]

    model_config = SettingsConfigDict(
        env_prefix="TEXT_",
        case_sensitive=False,
        extra="ignore",
    )


text_analysis_settings = TextAnalysisSettings()


__all__ = ["TextAnalysisSettings", "text_analysis_settings"]
