# src/summarization/domain/interfaces.py
"""
Domain interfaces for summarization module.
Follows Interface Segregation and Dependency Inversion principles.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from uuid import UUID
from src.summarization.domain.summary import Summary


class ISummarizationService(ABC):
    """Interface for core summarization operations."""
    
    @abstractmethod
    async def summarize(
        self, 
        text_content: str, 
        summary_id: Optional[UUID] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Summarize text content."""
        pass
    
    @abstractmethod
    async def batch_summarize(
        self, 
        texts: Dict[UUID, str], 
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[UUID, str]:
        """Summarize multiple texts in batch."""
        pass


class ISummaryValidator(ABC):
    """Interface for summary validation operations."""
    
    @abstractmethod
    def validate_input_text(self, text: str) -> None:
        """Validate input text for summarization."""
        pass
    
    @abstractmethod
    def validate_summary_quality(self, summary: str, original_text: str) -> None:
        """Validate generated summary quality."""
        pass
    
    @abstractmethod
    def validate_summary_length(self, summary: str, max_length: int) -> None:
        """Validate summary length constraints."""
        pass


class ISummaryMetricsService(ABC):
    """Interface for summary metrics operations."""
    
    @abstractmethod
    def record_processing_start(self, summary_id: UUID) -> None:
        """Record start of summary processing."""
        pass
    
    @abstractmethod
    def record_processing_success(
        self, 
        summary_id: UUID, 
        input_length: int, 
        output_length: int,
        provider: str
    ) -> None:
        """Record successful summary processing."""
        pass
    
    @abstractmethod
    def record_processing_failure(self, summary_id: UUID, error: str) -> None:
        """Record failed summary processing."""
        pass
    
    @abstractmethod
    def get_processing_stats(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """Get processing statistics."""
        pass


class ISummaryStateManager(ABC):
    """Interface for summary state management."""
    
    @abstractmethod
    async def update_status(
        self, 
        summary_id: UUID, 
        status: str, 
        error_message: Optional[str] = None
    ) -> None:
        """Update summary processing status."""
        pass
    
    @abstractmethod
    async def get_status(self, summary_id: UUID) -> Optional[str]:
        """Get current summary processing status."""
        pass
    
    @abstractmethod
    async def cleanup_old_states(self, days_to_keep: int = 7) -> int:
        """Clean up old processing states."""
        pass
"""
Domain interfaces for summarization module following SOLID principles.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from src.summarization.domain.summary import Summary


class ISummaryReader(ABC):
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


class ISummaryWriter(ABC):
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


class ISummaryProvider(ABC):
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


class ISummaryConfiguration(ABC):
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


class ISummaryHealthCheck(ABC):
    """Interface for health checks - SRP compliance."""
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check summarization provider health."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get summarization statistics."""
        pass


class ISummaryOperationLogger(ABC):
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


class ISummaryMetrics(ABC):
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


class ISummaryNotificationService(ABC):
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


class ISummaryStateManager(ABC):
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


class ISummaryProviderFactory(ABC):
    """Factory interface for creating summarization providers - DIP compliance."""
    
    @abstractmethod
    def create_provider(self, provider_type: str, config: SummaryConfiguration) -> SummaryProvider:
        """Create summarization provider instance."""
        pass
    
    @abstractmethod
    def get_available_providers(self) -> list[str]:
        """Get list of available provider types."""
        pass


class ISummaryOrchestrator(ABC):
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