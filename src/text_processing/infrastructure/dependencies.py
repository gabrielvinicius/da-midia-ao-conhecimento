# src/text_processing/infrastructure/dependencies.py
"""
Dependency injection setup for text processing module - DIP compliance.
"""
import os
from typing import Optional

from src.text_processing.domain.interfaces import (
    TextExtractorFactory,
    TextOperationLogger,
    TextMetrics,
    TextNotificationService,
    TextProcessingOrchestrator,
    TextValidator,
    TextProcessor,
    TextFormat
)
from src.text_processing.domain.services.text_coordinator import TextCoordinator
from src.text_processing.application.services.text_orchestrator import TextProcessingOrchestratorImpl
from src.text_processing.application.services.text_validator import DefaultTextValidator
from src.text_processing.application.services.text_processor import DefaultTextProcessor
from src.text_processing.infrastructure.factory import get_text_extractor_factory
from src.text_processing.infrastructure.logging import StructuredTextLogger, NoOpTextLogger
from src.text_processing.infrastructure.metrics import PrometheusTextMetrics, NoOpTextMetrics
from src.text_processing.infrastructure.notification_service import (
    WebSocketTextNotificationService, 
    NoOpTextNotificationService
)


class TextProcessingDependencyContainer:
    """
    Dependency injection container for text processing module.
    Follows DIP by managing dependencies through abstractions.
    """
    
    def __init__(self):
        self._factory: Optional[TextExtractorFactory] = None
        self._logger: Optional[TextOperationLogger] = None
        self._metrics: Optional[TextMetrics] = None
        self._notification_service: Optional[TextNotificationService] = None
        self._validator: Optional[TextValidator] = None
        self._processor: Optional[TextProcessor] = None
        self._orchestrator: Optional[TextProcessingOrchestrator] = None
    
    def get_text_extractor_factory(self) -> TextExtractorFactory:
        """Get text extractor factory."""
        if self._factory is None:
            self._factory = get_text_extractor_factory()
        return self._factory
    
    def get_text_logger(self) -> TextOperationLogger:
        """Get text operation logger."""
        if self._logger is None:
            if os.getenv("ENABLE_TEXT_PROCESSING_LOGGING", "true").lower() == "true":
                self._logger = StructuredTextLogger()
            else:
                self._logger = NoOpTextLogger()
        return self._logger
    
    def get_text_metrics(self) -> TextMetrics:
        """Get text processing metrics collector."""
        if self._metrics is None:
            if os.getenv("ENABLE_TEXT_PROCESSING_METRICS", "true").lower() == "true":
                self._metrics = PrometheusTextMetrics()
            else:
                self._metrics = NoOpTextMetrics()
        return self._metrics
    
    def get_notification_service(self) -> TextNotificationService:
        """Get notification service."""
        if self._notification_service is None:
            # This would be injected from the notifications module
            # For now, use no-op for testing
            self._notification_service = NoOpTextNotificationService()
        return self._notification_service
    
    def get_text_validator(self) -> TextValidator:
        """Get text validator."""
        if self._validator is None:
            min_length = int(os.getenv("TEXT_MIN_LENGTH", "10"))
            max_length = int(os.getenv("TEXT_MAX_LENGTH", "1000000"))
            min_word_count = int(os.getenv("TEXT_MIN_WORD_COUNT", "5"))
            
            allowed_languages = os.getenv("TEXT_ALLOWED_LANGUAGES", "").split(",")
            allowed_languages = [lang.strip() for lang in allowed_languages if lang.strip()]
            
            self._validator = DefaultTextValidator(
                min_length=min_length,
                max_length=max_length,
                min_word_count=min_word_count,
                allowed_languages=allowed_languages if allowed_languages else None
            )
        return self._validator
    
    def get_text_processor(self) -> TextProcessor:
        """Get text processor."""
        if self._processor is None:
            normalize_whitespace = os.getenv("TEXT_NORMALIZE_WHITESPACE", "true").lower() == "true"
            remove_extra_punctuation = os.getenv("TEXT_REMOVE_EXTRA_PUNCTUATION", "true").lower() == "true"
            preserve_structure = os.getenv("TEXT_PRESERVE_STRUCTURE", "true").lower() == "true"
            min_paragraph_length = int(os.getenv("TEXT_MIN_PARAGRAPH_LENGTH", "50"))
            
            self._processor = DefaultTextProcessor(
                normalize_whitespace=normalize_whitespace,
                remove_extra_punctuation=remove_extra_punctuation,
                preserve_structure=preserve_structure,
                min_paragraph_length=min_paragraph_length
            )
        return self._processor
    
    def get_orchestrator(self) -> TextProcessingOrchestrator:
        """Get high-level text processing orchestrator."""
        if self._orchestrator is None:
            # Create extractor based on default format
            default_format = self._get_default_format()
            extractor = self._create_extractor(default_format)
            
            # Create coordinator
            coordinator = TextCoordinator(
                extractor=extractor,
                validator=self.get_text_validator(),
                processor=self.get_text_processor(),
                logger=self.get_text_logger(),
                metrics=self.get_text_metrics(),
                notification_service=self.get_notification_service()
            )
            
            # Create orchestrator
            self._orchestrator = TextProcessingOrchestratorImpl(
                extractor_factory=self.get_text_extractor_factory(),
                coordinator=coordinator
            )
        
        return self._orchestrator
    
    def _get_default_format(self) -> TextFormat:
        """Get default text format from environment."""
        format_name = os.getenv("DEFAULT_TEXT_FORMAT", "pdf").lower()
        format_mapping = {
            "pdf": TextFormat.PDF,
            "docx": TextFormat.DOCX,
            "txt": TextFormat.TXT,
            "markdown": TextFormat.MARKDOWN,
            "md": TextFormat.MARKDOWN
        }
        return format_mapping.get(format_name, TextFormat.PDF)
    
    def _create_extractor(self, format_type: TextFormat):
        """Create text extractor for specific format."""
        factory = self.get_text_extractor_factory()
        
        # Get configuration parameters from environment
        if format_type == TextFormat.PDF:
            max_file_size = int(os.getenv("PDF_MAX_FILE_SIZE", str(50 * 1024 * 1024)))
            extract_images = os.getenv("PDF_EXTRACT_IMAGES", "false").lower() == "true"
            extract_tables = os.getenv("PDF_EXTRACT_TABLES", "false").lower() == "true"
            preserve_layout = os.getenv("PDF_PRESERVE_LAYOUT", "false").lower() == "true"
            
            return factory.create_extractor_with_params(
                format_type,
                max_file_size=max_file_size,
                extract_images=extract_images,
                extract_tables=extract_tables,
                preserve_layout=preserve_layout
            )
        
        elif format_type == TextFormat.DOCX:
            max_file_size = int(os.getenv("DOCX_MAX_FILE_SIZE", str(30 * 1024 * 1024)))
            extract_tables = os.getenv("DOCX_EXTRACT_TABLES", "true").lower() == "true"
            extract_headers_footers = os.getenv("DOCX_EXTRACT_HEADERS_FOOTERS", "true").lower() == "true"
            preserve_formatting = os.getenv("DOCX_PRESERVE_FORMATTING", "false").lower() == "true"
            
            return factory.create_extractor_with_params(
                format_type,
                max_file_size=max_file_size,
                extract_tables=extract_tables,
                extract_headers_footers=extract_headers_footers,
                preserve_formatting=preserve_formatting
            )
        
        elif format_type in [TextFormat.TXT, TextFormat.MARKDOWN]:
            max_file_size = int(os.getenv("TEXT_MAX_FILE_SIZE", str(10 * 1024 * 1024)))
            encoding = os.getenv("TEXT_ENCODING", "auto")
            preserve_line_breaks = os.getenv("TEXT_PRESERVE_LINE_BREAKS", "true").lower() == "true"
            normalize_whitespace = os.getenv("TEXT_NORMALIZE_WHITESPACE", "true").lower() == "true"
            
            return factory.create_extractor_with_params(
                format_type,
                max_file_size=max_file_size,
                encoding=encoding,
                preserve_line_breaks=preserve_line_breaks,
                normalize_whitespace=normalize_whitespace
            )
        
        else:
            return factory.create_extractor(format_type)


# Global container instance
_container = TextProcessingDependencyContainer()


def get_text_processing_orchestrator() -> TextProcessingOrchestrator:
    """Dependency provider for text processing orchestrator."""
    return _container.get_orchestrator()


def get_text_extractor_factory_dep() -> TextExtractorFactory:
    """Dependency provider for text extractor factory."""
    return _container.get_text_extractor_factory()


def get_text_logger_dep() -> TextOperationLogger:
    """Dependency provider for text logger."""
    return _container.get_text_logger()


def get_text_metrics_dep() -> TextMetrics:
    """Dependency provider for text metrics."""
    return _container.get_text_metrics()


def get_text_validator_dep() -> TextValidator:
    """Dependency provider for text validator."""
    return _container.get_text_validator()


def get_text_processor_dep() -> TextProcessor:
    """Dependency provider for text processor."""
    return _container.get_text_processor()