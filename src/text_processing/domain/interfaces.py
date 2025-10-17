# src/text_processing/domain/interfaces.py
"""
Domain interfaces for text processing module following SOLID principles.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from enum import Enum


class TextFormat(str, Enum):
    """Supported text formats."""
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    RTF = "rtf"
    HTML = "html"
    MARKDOWN = "md"


class TextExtractor(ABC):
    """Interface for text extraction - ISP compliance."""
    
    @property
    @abstractmethod
    def supported_formats(self) -> List[TextFormat]:
        """Get supported text formats."""
        pass
    
    @abstractmethod
    async def extract_text(self, file_content: bytes, format_type: TextFormat) -> str:
        """Extract text from file content."""
        pass
    
    @abstractmethod
    async def validate_format(self, file_content: bytes, format_type: TextFormat) -> bool:
        """Validate if file content matches expected format."""
        pass


class TextValidator(ABC):
    """Interface for text validation - ISP compliance."""
    
    @abstractmethod
    async def validate_content(self, text: str) -> bool:
        """Validate extracted text content."""
        pass
    
    @abstractmethod
    async def get_content_stats(self, text: str) -> Dict[str, Any]:
        """Get text content statistics."""
        pass
    
    @abstractmethod
    async def detect_language(self, text: str) -> Optional[str]:
        """Detect text language."""
        pass


class TextProcessor(ABC):
    """Interface for text processing - ISP compliance."""
    
    @abstractmethod
    async def clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        pass
    
    @abstractmethod
    async def extract_metadata(self, text: str) -> Dict[str, Any]:
        """Extract metadata from text."""
        pass
    
    @abstractmethod
    async def chunk_text(self, text: str, chunk_size: int) -> List[str]:
        """Split text into chunks."""
        pass


class TextConfiguration(ABC):
    """Interface for text processing configuration - SRP compliance."""
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Get text processing configuration."""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate configuration."""
        pass
    
    @abstractmethod
    def get_max_file_size(self) -> int:
        """Get maximum file size in bytes."""
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[TextFormat]:
        """Get supported text formats."""
        pass


class TextHealthCheck(ABC):
    """Interface for health checks - SRP compliance."""
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Check text processing health."""
        pass
    
    @abstractmethod
    async def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        pass


class TextOperationLogger(ABC):
    """Interface for operation logging - SRP compliance."""
    
    @abstractmethod
    async def log_operation(
        self, 
        operation: str, 
        media_id: str,
        format_type: str,
        success: bool,
        duration: float,
        text_length: Optional[int] = None,
        error: Optional[Exception] = None
    ) -> None:
        """Log text processing operation."""
        pass


class TextMetrics(ABC):
    """Interface for metrics collection - SRP compliance."""
    
    @abstractmethod
    async def record_operation(
        self, 
        operation: str, 
        format_type: str,
        duration: float,
        success: bool,
        file_size: int,
        text_length: int
    ) -> None:
        """Record text processing metrics."""
        pass


class TextNotificationService(ABC):
    """Interface for notifications - SRP compliance."""
    
    @abstractmethod
    async def notify_started(self, media_id: str, user_id: str) -> None:
        """Notify text processing started."""
        pass
    
    @abstractmethod
    async def notify_completed(
        self, 
        media_id: str, 
        user_id: str, 
        text_length: int
    ) -> None:
        """Notify text processing completed."""
        pass
    
    @abstractmethod
    async def notify_failed(
        self, 
        media_id: str, 
        user_id: str, 
        error: str
    ) -> None:
        """Notify text processing failed."""
        pass


class TextExtractorFactory(ABC):
    """Factory interface for creating text extractors - DIP compliance."""
    
    @abstractmethod
    def create_extractor(self, format_type: TextFormat) -> TextExtractor:
        """Create text extractor for specific format."""
        pass
    
    @abstractmethod
    def get_supported_formats(self) -> List[TextFormat]:
        """Get list of supported formats."""
        pass


class TextProcessingOrchestrator(ABC):
    """High-level orchestrator interface - DIP compliance."""
    
    @abstractmethod
    async def process_text_file(
        self, 
        media_id: str, 
        file_content: bytes,
        format_type: TextFormat,
        user_id: str
    ) -> str:
        """Process complete text extraction workflow."""
        pass
    
    @abstractmethod
    async def get_processing_status(self, media_id: str) -> Optional[str]:
        """Get text processing status."""
        pass