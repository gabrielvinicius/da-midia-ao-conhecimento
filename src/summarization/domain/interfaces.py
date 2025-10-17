# src/summarization/domain/interfaces.py
"""
Domain interfaces for summarization module following SOLID principles.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from src.summarization.domain.summary import Summary


class SummaryReader(ABC):
    """Interface for read operations - ISP compliance."""
    
    @abstractmethod
    async def find_by_media_id(self, media_id: str) -> Optional[Summary]:
        """Find summary by media ID."""
        pass
    
    @abstractmethod
    async def find_by_id(self, summary_id: str) -> Optional[Summary]:
        """Find summary by ID."""
        pass
    
    @abstractmethod
    async def exists_for_media(self, media_id: str) -> bool:
        """Check if summary exists for media."""
        pass


class SummaryWriter(ABC):
    """Interface for write operations - ISP compliance."""
    
    @abstractmethod
    async def save(self, summary: Summary) -> Summary:
        """Save summary."""
        pass
    
    @abstractmethod
    async def delete_by_media_id(self, media_id: str) -> bool:
        """Delete summary by media ID."""
        pass


class ISummaryRepository(SummaryReader, SummaryWriter):
    """Complete repository interface combining read/write operations."""
    pass


class SummaryProvider(ABC):
    """Interface for summarization providers - ISP compliance."""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier."""
        pass
    
    @abstractmethod
    async def summarize(self, text: str) -> str:
        """Generate summary from text."""
        pass
    
    @abstractmethod
    async def get_capabilities(self) -> Dict[str, Any]:
        """Get provider capabilities."""
        pass


class SummaryConfiguration(ABC):
    """Interface for summarization configuration - SRP compliance."""
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Get summarization configuration."""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate configuration."""
        pass
    
    @abstractmethod
    def get_max_input_length(self) -> int:
        """Get maximum input text length."""
        pass
    
    @abstractmethod
    def get_max_output_length(self) -> int:
        """Get maximum output summary length."""
        pass


class SummaryHealthCheck(ABC):
    """Interface for health checks - SRP compliance."""
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check summarization provider health."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get summarization statistics."""
        pass


class SummaryOperationLogger(ABC):
    """Interface for operation logging - SRP compliance."""
    
    @abstractmethod
    async def log_operation(
        self, 
        operation: str, 
        media_id: str,
        provider: str,
        success: bool,
        duration: float,
        error: Optional[Exception] = None
    ) -> None:
        """Log summarization operation."""
        pass


class SummaryMetrics(ABC):
    """Interface for metrics collection - SRP compliance."""
    
    @abstractmethod
    async def record_operation(
        self, 
        operation: str, 
        provider: str,
        duration: float,
        success: bool,
        input_length: int,
        output_length: int
    ) -> None:
        """Record summarization metrics."""
        pass


class SummaryNotificationService(ABC):
    """Interface for notifications - SRP compliance."""
    
    @abstractmethod
    async def notify_started(self, summary: Summary, user_id: str) -> None:
        """Notify summarization started."""
        pass
    
    @abstractmethod
    async def notify_completed(self, summary: Summary, user_id: str) -> None:
        """Notify summarization completed."""
        pass
    
    @abstractmethod
    async def notify_failed(self, summary: Summary, user_id: str, error: str) -> None:
        """Notify summarization failed."""
        pass


class SummaryStateManager(ABC):
    """Interface for state management - SRP compliance."""
    
    @abstractmethod
    async def start_processing(self, media_id: str, provider: str) -> Summary:
        """Start processing and return summary."""
        pass
    
    @abstractmethod
    async def complete_processing(self, summary: Summary, text: str) -> Summary:
        """Complete processing with result."""
        pass
    
    @abstractmethod
    async def fail_processing(self, summary: Summary, error: str) -> Summary:
        """Mark processing as failed."""
        pass


class SummaryProviderFactory(ABC):
    """Factory interface for creating summarization providers - DIP compliance."""
    
    @abstractmethod
    def create_provider(self, provider_type: str, config: SummaryConfiguration) -> SummaryProvider:
        """Create summarization provider instance."""
        pass
    
    @abstractmethod
    def get_available_providers(self) -> list[str]:
        """Get list of available provider types."""
        pass


class SummaryOrchestrator(ABC):
    """High-level orchestrator interface - DIP compliance."""
    
    @abstractmethod
    async def process_summarization(
        self, 
        media_id: str, 
        text_content: str, 
        provider: str,
        user_id: str
    ) -> Summary:
        """Process complete summarization workflow."""
        pass
    
    @abstractmethod
    async def get_summary(self, media_id: str) -> Optional[Summary]:
        """Get existing summary."""
        pass