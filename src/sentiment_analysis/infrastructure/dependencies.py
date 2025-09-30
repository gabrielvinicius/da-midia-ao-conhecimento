# src/sentiment_analysis/infrastructure/dependencies.py
from functools import lru_cache
from .interfaces import ISentimentAnalysisService
from .huggingface_sentiment_service import HuggingFaceSentimentAnalysisService

# Use lru_cache to ensure the service is a singleton, as loading the model is expensive.
@lru_cache(maxsize=None)
def get_sentiment_analysis_service() -> ISentimentAnalysisService:
    """Dependency provider for the sentiment analysis service."""
    return HuggingFaceSentimentAnalysisService()
