"""
Domain interfaces for sentiment analysis module.
Follows Dependency Inversion Principle (DIP).
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
from uuid import UUID
from enum import Enum
from datetime import datetime


class SentimentLabel(Enum):
    """Standard sentiment labels."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"
    ERROR = "error"


class SentimentProvider(Enum):
    """Available sentiment analysis providers."""
    HUGGINGFACE = "huggingface"
    OPENAI = "openai"
    GOOGLE_CLOUD = "google_cloud"
    AZURE_COGNITIVE = "azure_cognitive"
    AWS_COMPREHEND = "aws_comprehend"
    TEXTBLOB = "textblob"
    VADER = "vader"
    CUSTOM = "custom"


class AnalysisGranularity(Enum):
    """Granularity levels for sentiment analysis."""
    DOCUMENT = "document"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    PHRASE = "phrase"


class ISentimentAnalysisService(ABC):
    """Interface for sentiment analysis service operations."""
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """Get the name of the sentiment analysis provider."""
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        pass
    
    @abstractmethod
    async def analyze(self, text: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze sentiment of text.
        
        Args:
            text: Text to analyze
            language: Optional language code
            
        Returns:
            Dictionary with sentiment analysis results
        """
        pass
    
    @abstractmethod
    async def analyze_batch(self, texts: List[str], language: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Analyze sentiment of multiple texts in batch.
        
        Args:
            texts: List of texts to analyze
            language: Optional language code
            
        Returns:
            List of sentiment analysis results
        """
        pass
    
    @abstractmethod
    async def analyze_with_granularity(
        self, 
        text: str, 
        granularity: AnalysisGranularity,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze sentiment with specific granularity.
        
        Args:
            text: Text to analyze
            granularity: Level of granularity for analysis
            language: Optional language code
            
        Returns:
            Granular sentiment analysis results
        """
        pass
    
    @abstractmethod
    async def get_confidence_threshold(self) -> float:
        """Get confidence threshold for reliable results."""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the service."""
        pass


class ISentimentRepository(ABC):
    """Interface for sentiment analysis repository operations."""
    
    @abstractmethod
    async def save(self, sentiment_result) -> Any:
        """Save sentiment analysis result."""
        pass
    
    @abstractmethod
    async def find_by_id(self, result_id: UUID) -> Optional[Any]:
        """Find sentiment result by ID."""
        pass
    
    @abstractmethod
    async def find_by_media_id(self, media_id: UUID) -> Optional[Any]:
        """Find sentiment result by media ID."""
        pass
    
    @abstractmethod
    async def find_by_user_id(self, user_id: UUID) -> List[Any]:
        """Find sentiment results by user ID."""
        pass
    
    @abstractmethod
    async def find_by_sentiment_label(self, label: SentimentLabel) -> List[Any]:
        """Find results by sentiment label."""
        pass
    
    @abstractmethod
    async def delete(self, result_id: UUID) -> bool:
        """Delete sentiment analysis result."""
        pass
    
    @abstractmethod
    async def get_sentiment_statistics(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get sentiment analysis statistics."""
        pass


class ISentimentQueries(ABC):
    """Interface for sentiment analysis query operations."""
    
    @abstractmethod
    async def get_by_media_id(self, media_id: UUID) -> Optional[Any]:
        """Get sentiment analysis by media ID."""
        pass
    
    @abstractmethod
    async def get_user_sentiment_summary(self, user_id: UUID) -> Dict[str, Any]:
        """Get sentiment summary for a user."""
        pass
    
    @abstractmethod
    async def get_sentiment_trends(
        self, 
        user_id: Optional[UUID] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get sentiment trends over time."""
        pass
    
    @abstractmethod
    async def get_comparative_analysis(
        self,
        media_ids: List[UUID]
    ) -> Dict[str, Any]:
        """Get comparative sentiment analysis for multiple media."""
        pass


class ISentimentAnalyzer(ABC):
    """Interface for high-level sentiment analysis operations."""
    
    @abstractmethod
    async def analyze_media(
        self,
        media_id: UUID,
        provider: SentimentProvider = SentimentProvider.HUGGINGFACE,
        options: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """
        Analyze sentiment for media content.
        
        Args:
            media_id: ID of media to analyze
            provider: Sentiment analysis provider to use
            options: Additional analysis options
            
        Returns:
            Analysis result ID
        """
        pass
    
    @abstractmethod
    async def reanalyze_media(
        self,
        media_id: UUID,
        provider: Optional[SentimentProvider] = None
    ) -> UUID:
        """Re-analyze media with different provider or updated settings."""
        pass
    
    @abstractmethod
    async def analyze_text_directly(
        self,
        text: str,
        provider: SentimentProvider = SentimentProvider.HUGGINGFACE,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Analyze sentiment of text directly without storing."""
        pass
    
    @abstractmethod
    async def get_provider_comparison(
        self,
        text: str,
        providers: List[SentimentProvider]
    ) -> Dict[str, Dict[str, Any]]:
        """Compare results across multiple providers."""
        pass


class ISentimentMetrics(ABC):
    """Interface for sentiment analysis metrics operations."""
    
    @abstractmethod
    async def track_analysis_request(
        self,
        provider: SentimentProvider,
        success: bool,
        duration: float,
        text_length: int
    ) -> None:
        """Track sentiment analysis request metrics."""
        pass
    
    @abstractmethod
    async def get_provider_performance(
        self,
        provider: SentimentProvider
    ) -> Dict[str, Any]:
        """Get performance metrics for a provider."""
        pass
    
    @abstractmethod
    async def get_accuracy_metrics(
        self,
        provider: SentimentProvider
    ) -> Dict[str, Any]:
        """Get accuracy metrics for a provider."""
        pass
    
    @abstractmethod
    async def get_usage_statistics(
        self,
        time_range: str = "30d"
    ) -> Dict[str, Any]:
        """Get usage statistics for sentiment analysis."""
        pass


class ISentimentCache(ABC):
    """Interface for sentiment analysis caching operations."""
    
    @abstractmethod
    async def get_cached_result(self, text_hash: str, provider: SentimentProvider) -> Optional[Dict[str, Any]]:
        """Get cached sentiment analysis result."""
        pass
    
    @abstractmethod
    async def cache_result(
        self,
        text_hash: str,
        provider: SentimentProvider,
        result: Dict[str, Any],
        ttl: int = 3600
    ) -> None:
        """Cache sentiment analysis result."""
        pass
    
    @abstractmethod
    async def invalidate_cache(self, text_hash: str) -> None:
        """Invalidate cached results for text."""
        pass
    
    @abstractmethod
    async def get_cache_statistics(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        pass


class ISentimentValidator(ABC):
    """Interface for sentiment analysis validation operations."""
    
    @abstractmethod
    def validate_text_input(self, text: str) -> Dict[str, Any]:
        """Validate text input for analysis."""
        pass
    
    @abstractmethod
    def validate_analysis_result(self, result: Dict[str, Any]) -> bool:
        """Validate sentiment analysis result format."""
        pass
    
    @abstractmethod
    def normalize_sentiment_score(self, score: float, provider: SentimentProvider) -> float:
        """Normalize sentiment score across providers."""
        pass
    
    @abstractmethod
    def validate_confidence_threshold(self, result: Dict[str, Any], threshold: float) -> bool:
        """Check if result meets confidence threshold."""
        pass


class ISentimentAggregator(ABC):
    """Interface for sentiment analysis aggregation operations."""
    
    @abstractmethod
    async def aggregate_document_sentiment(
        self,
        sentence_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate sentence-level sentiments to document level."""
        pass
    
    @abstractmethod
    async def aggregate_temporal_sentiment(
        self,
        results: List[Dict[str, Any]],
        time_window: str
    ) -> Dict[str, Any]:
        """Aggregate sentiment over time windows."""
        pass
    
    @abstractmethod
    async def calculate_sentiment_distribution(
        self,
        results: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate distribution of sentiment labels."""
        pass
    
    @abstractmethod
    async def generate_sentiment_insights(
        self,
        results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate insights from sentiment analysis results."""
        pass


class ISentimentEventHandler(ABC):
    """Interface for sentiment analysis event handling."""
    
    @abstractmethod
    async def handle_transcription_completed(self, event: Dict[str, Any]) -> None:
        """Handle transcription completion event."""
        pass
    
    @abstractmethod
    async def handle_sentiment_analysis_completed(self, event: Dict[str, Any]) -> None:
        """Handle sentiment analysis completion event."""
        pass
    
    @abstractmethod
    async def handle_media_uploaded(self, event: Dict[str, Any]) -> None:
        """Handle media upload event."""
        pass


class ISentimentConfigurationService(ABC):
    """Interface for sentiment analysis configuration management."""
    
    @abstractmethod
    async def get_provider_config(self, provider: SentimentProvider) -> Dict[str, Any]:
        """Get configuration for a provider."""
        pass
    
    @abstractmethod
    async def update_provider_config(
        self,
        provider: SentimentProvider,
        config: Dict[str, Any]
    ) -> bool:
        """Update provider configuration."""
        pass
    
    @abstractmethod
    async def get_analysis_settings(self, user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Get analysis settings for user or system."""
        pass
    
    @abstractmethod
    async def update_analysis_settings(
        self,
        settings: Dict[str, Any],
        user_id: Optional[UUID] = None
    ) -> bool:
        """Update analysis settings."""
        pass


class ISentimentModelManager(ABC):
    """Interface for sentiment analysis model management."""
    
    @abstractmethod
    async def load_model(self, provider: SentimentProvider, model_name: str) -> bool:
        """Load a specific model for a provider."""
        pass
    
    @abstractmethod
    async def unload_model(self, provider: SentimentProvider) -> bool:
        """Unload model to free resources."""
        pass
    
    @abstractmethod
    async def get_model_info(self, provider: SentimentProvider) -> Dict[str, Any]:
        """Get information about loaded model."""
        pass
    
    @abstractmethod
    async def benchmark_model(self, provider: SentimentProvider, test_data: List[str]) -> Dict[str, Any]:
        """Benchmark model performance."""
        pass
    
    @abstractmethod
    async def update_model(self, provider: SentimentProvider, model_path: str) -> bool:
        """Update model for a provider."""
        pass