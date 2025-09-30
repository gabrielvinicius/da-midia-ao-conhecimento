# src/sentiment_analysis/infrastructure/dependencies.py
from functools import lru_cache
from .interfaces import ISentimentAnalysisService, ITopicModelingService
from .huggingface_sentiment_service import HuggingFaceSentimentAnalysisService
from .sklearn_topic_modeling_service import SklearnTopicModelingService

# Use lru_cache to ensure services are singletons, as loading models can be expensive.

@lru_cache(maxsize=None)
def get_sentiment_analysis_service() -> ISentimentAnalysisService:
    """Dependency provider for the sentiment analysis service."""
    return HuggingFaceSentimentAnalysisService()

@lru_cache(maxsize=None)
def get_topic_modeling_service() -> ITopicModelingService:
    """Dependency provider for the topic modeling service."""
    return SklearnTopicModelingService()
