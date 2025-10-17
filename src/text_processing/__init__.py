# src/text_processing/__init__.py
"""
Text processing module following SOLID principles.

This module provides a clean, extensible text extraction and processing abstraction that follows:
- SRP: Each class has a single responsibility
- OCP: Easy to extend with new extractors without modification
- LSP: All extractors implement the same interface contract
- ISP: Segregated interfaces for different concerns
- DIP: High-level modules depend on abstractions

Usage:
    from src.text_processing import get_text_processing_orchestrator
    
    # Get orchestrator (auto-configured from environment)
    orchestrator = get_text_processing_orchestrator()
    
    # Process text file
    text_content = await orchestrator.process_text_file(
        media_id="123",
        file_content=file_bytes,
        format_type=TextFormat.PDF,
        user_id="user123"
    )
    
    # Check processing status
    status = await orchestrator.get_processing_status("123")
"""

# Domain exports
from src.text_processing.domain.interfaces import (
    TextExtractor,
    TextValidator,
    TextProcessor,
    TextExtractorFactory,
    TextConfiguration,
    TextProcessingOrchestrator,
    TextFormat
)

# Application exports
from src.text_processing.application.commands.process_text_command import ProcessTextCommand
from src.text_processing.application.commands.process_text_command_handler import ProcessTextCommandHandler
from src.text_processing.application.services.text_validator import DefaultTextValidator
from src.text_processing.application.services.text_processor import DefaultTextProcessor

# Infrastructure exports
from src.text_processing.infrastructure.dependencies import (
    get_text_processing_orchestrator,
    get_text_extractor_factory_dep,
    get_text_logger_dep,
    get_text_metrics_dep,
    get_text_validator_dep,
    get_text_processor_dep
)
from src.text_processing.infrastructure.factory import register_text_extractor

# Extractor implementations
from src.text_processing.infrastructure.extractors.pdf_extractor import (
    PDFTextExtractor, 
    PDFConfiguration
)
from src.text_processing.infrastructure.extractors.docx_extractor import (
    DOCXTextExtractor, 
    DOCXConfiguration
)
from src.text_processing.infrastructure.extractors.plain_text_extractor import (
    PlainTextExtractor, 
    PlainTextConfiguration
)

__all__ = [
    # Domain
    "TextExtractor",
    "TextValidator",
    "TextProcessor",
    "TextExtractorFactory",
    "TextConfiguration",
    "TextProcessingOrchestrator",
    "TextFormat",
    
    # Application
    "ProcessTextCommand",
    "ProcessTextCommandHandler",
    "DefaultTextValidator",
    "DefaultTextProcessor",
    
    # Infrastructure
    "get_text_processing_orchestrator",
    "get_text_extractor_factory_dep",
    "get_text_logger_dep",
    "get_text_metrics_dep",
    "get_text_validator_dep",
    "get_text_processor_dep",
    "register_text_extractor",
    
    # Extractors
    "PDFTextExtractor",
    "PDFConfiguration",
    "DOCXTextExtractor",
    "DOCXConfiguration",
    "PlainTextExtractor",
    "PlainTextConfiguration",
]