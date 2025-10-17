# src/topic_modeling/domain/interfaces.py
"""
Domain interfaces for topic modeling module following SOLID principles.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

from src.topic_modeling.domain.topic_modeling import TopicModelingResult


class TopicModelingReader(ABC):
    """Interface for read operations - ISP compliance."""
    
    @abstractmethod
    async def find_by_id(self, result_id: UUID) -> Optional[TopicModelingResult]:
        """Find topic modeling result by ID."""
        pass
    
    @abstractmethod
    async def find_by_media_id(self, media_id: UUID) -> Optional[TopicModelingResult]:
        """Find topic modeling result by media ID."""
        pass
    
    @abstractmethod
    async def exists_for_media(self, media_id: UUID) -> bool:
        """Check if topic modeling result exists for media."""
        pass


class TopicModelingWriter(ABC):
    """Interface for write operations - ISP compliance."""
    
    @abstractmethod
    async def save(self, result: TopicModelingResult) -> TopicModelingResult:
        """Save topic modeling result."""
        pass
    
    @abstractmethod
    async def delete(self, result_id: UUID) -> bool:
        """Delete topic modeling result."""
        pass


class ITopicModelingRepository(TopicModelingReader, TopicModelingWriter):
    """Complete repository interface combining read/write operations."""
    pass


class TopicModelingProvider(ABC):
    """Interface for topic modeling providers - ISP compliance."""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier."""
        pass
    
    @abstractmethod
    async def extract_topics(
        self, 
        text: str, 
        language: str = "en",
        num_topics: int = 5,
        num_words_per_topic: int = 5
    ) -> List[Dict[str, Any]]:
        """Extract topics from text."""
        pass
    
    @abstractmethod
    async def get_supported_languages(self) -> List[str]:
        """Get supported languages."""
        pass
    
    @abstractmethod
    async def get_capabilities(self) -> Dict[str, Any]:
        """Get provider capabilities."""
        pass


class TextPreprocessor(ABC):
    """Interface for text preprocessing - ISP compliance."""
    
    @abstractmethod
    async def preprocess_text(self, text: str, language: str) -> str:
        """Preprocess text for topic modeling."""
        pass
    
    @abstractmethod
    async def validate_text(self, text: str) -> bool:
        """Validate text for topic modeling."""
        pass
    
    @abstractmethod
    async def get_text_stats(self, text: str) -> Dict[str, Any]:
        """Get text statistics."""
        pass


class TopicValidator(ABC):
    """Interface for topic validation - ISP compliance."""
    
    @abstractmethod
    async def validate_topics(self, topics: List[Dict[str, Any]]) -> bool:
        """Validate extracted topics."""
        pass
    
    @abstractmethod
    async def calculate_coherence_score(self, topics: List[Dict[str, Any]]) -> float:
        """Calculate topic coherence score."""
        pass
    
    @abstractmethod
    async def filter_topics(
        self, 
        topics: List[Dict[str, Any]], 
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """Filter topics by quality score."""
        pass


class TopicModelingConfiguration(ABC):
    """Interface for topic modeling configuration - SRP compliance."""
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Get topic modeling configuration."""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate configuration."""
        pass
    
    @abstractmethod
    def get_supported_languages(self) -> List[str]:
        """Get supported languages."""
        pass
    
    @abstractmethod
    def get_max_text_length(self) -> int:
        """Get maximum text length."""
        pass


class TopicModelingHealthCheck(ABC):
    """Interface for health checks - SRP compliance."""
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check topic modeling provider health."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get topic modeling statistics."""
        pass


class TopicModelingOperationLogger(ABC):
    """Interface for operation logging - SRP compliance."""
    
    @abstractmethod
    async def log_operation(
        self, 
        operation: str, 
        media_id: str,
        provider: str,
        language: str,
        success: bool,
        duration: float,
        num_topics: int = 0,
        text_length: int = 0,
        error: Optional[Exception] = None
    ) -> None:
        """Log topic modeling operation."""
        pass


class TopicModelingMetrics(ABC):
    """Interface for metrics collection - SRP compliance."""
    
    @abstractmethod
    async def record_operation(
        self, 
        operation: str, 
        provider: str,
        language: str,
        duration: float,
        success: bool,
        text_length: int,
        num_topics: int,
        coherence_score: float
    ) -> None:
        """Record topic modeling metrics."""
        pass


class TopicModelingNotificationService(ABC):
    """Interface for notifications - SRP compliance."""
    
    @abstractmethod
    async def notify_started(self, media_id: str, user_id: str, provider: str) -> None:
        """Notify topic modeling started."""
        pass
    
    @abstractmethod
    async def notify_completed(
        self, 
        media_id: str, 
        user_id: str, 
        topics: List[Dict[str, Any]]
    ) -> None:
        """Notify topic modeling completed."""
        pass
    
    @abstractmethod
    async def notify_failed(
        self, 
        media_id: str, 
        user_id: str, 
        error: str
    ) -> None:
        """Notify topic modeling failed."""
        pass


class TopicModelingStateManager(ABC):
    """Interface for state management - SRP compliance."""
    
    @abstractmethod
    async def start_processing(
        self, 
        media_id: str, 
        provider: str,
        language: str
    ) -> TopicModelingResult:
        """Start processing and return result."""
        pass
    
    @abstractmethod
    async def complete_processing(
        self, 
        result: TopicModelingResult, 
        topics: List[Dict[str, Any]]
    ) -> TopicModelingResult:
        """Complete processing with topics."""
        pass
    
    @abstractmethod
    async def fail_processing(
        self, 
        result: TopicModelingResult, 
        error: str
    ) -> TopicModelingResult:
        """Mark processing as failed."""
        pass


class TopicModelingProviderFactory(ABC):
    """Factory interface for creating topic modeling providers - DIP compliance."""
    
    @abstractmethod
    def create_provider(
        self, 
        provider_type: str, 
        config: TopicModelingConfiguration
    ) -> TopicModelingProvider:
        """Create topic modeling provider instance."""
        pass
    
    @abstractmethod
    def get_available_providers(self) -> List[str]:
        """Get list of available provider types."""
        pass


class TopicModelingOrchestrator(ABC):
    """High-level orchestrator interface - DIP compliance."""
    
    @abstractmethod
    async def process_topic_modeling(
        self, 
        media_id: str, 
        text_content: str,
        language: str,
        provider: str,
        user_id: str,
        num_topics: int = 5
    ) -> TopicModelingResult:
        """Process complete topic modeling workflow."""
        pass
    
    @abstractmethod
    async def get_topics(self, media_id: str) -> Optional[TopicModelingResult]:
        """Get existing topic modeling result."""
        pass
    
    @abstractmethod
    async def retry_failed_modeling(
        self, 
        media_id: str, 
        text_content: str,
        language: str,
        provider: str,
        user_id: str,
        num_topics: int = 5
    ) -> TopicModelingResult:
        """Retry failed topic modeling."""
        pass