# src/sentiment_analysis/bootstrap.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from .application.queries.sentiment_analysis_queries import SentimentAnalysisQueries
from .application.services.sentiment_analyzer import SentimentAnalyzer
from .infrastructure.sentiment_analysis_repository import SentimentAnalysisRepository
from .infrastructure.huggingface_sentiment_service import HuggingFaceSentimentAnalysisService

def bootstrap_sentiment_analysis_module(db_session: AsyncSession) -> Dict[str, Any]:
    """
    Constructs and returns the services for the sentiment analysis module following SOLID principles.
    
    All services depend on interfaces for maximum flexibility and testability.
    """
    # Repository (implements ISentimentRepository)
    repository = SentimentAnalysisRepository(db=db_session)
    
    # Queries service (legacy)
    queries = SentimentAnalysisQueries(repository=repository)
    
    # Create sentiment services dict for the analyzer
    huggingface_service = HuggingFaceSentimentAnalysisService()
    sentiment_services = {
        "huggingface": huggingface_service,
        # Add other providers as they become available
    }
    
    # Get media repository (would be injected from media management module)
    media_repository = None  # Placeholder - would be injected
    
    # New SOLID sentiment analyzer
    sentiment_analyzer = SentimentAnalyzer(
        sentiment_services=sentiment_services,
        sentiment_repository=repository,
        media_repository=media_repository,
        cache_service=None,       # Would be injected from cache module
        validator_service=None,   # Would be injected or created
        metrics_service=None      # Would be injected from metrics module
    )

    return {
        # New SOLID services
        "sentiment_analyzer": sentiment_analyzer,
        "sentiment_services": sentiment_services,
        
        # Legacy services for backward compatibility
        "sentiment_analysis_repository": repository,
        "sentiment_analysis_queries": queries,
    }
