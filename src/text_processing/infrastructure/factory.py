# src/text_processing/infrastructure/factory.py
"""
Text extractor factory implementation - DIP and OCP compliance.
"""
from typing import Dict, Type, Callable, List
from src.text_processing.domain.interfaces import TextExtractorFactory, TextExtractor, TextConfiguration, TextFormat
from src.text_processing.infrastructure.extractors.pdf_extractor import PDFTextExtractor, PDFConfiguration
from src.text_processing.infrastructure.extractors.docx_extractor import DOCXTextExtractor, DOCXConfiguration
from src.text_processing.infrastructure.extractors.plain_text_extractor import PlainTextExtractor, PlainTextConfiguration


class ConcreteTextExtractorFactory(TextExtractorFactory):
    """
    Concrete factory for creating text extractors.
    Follows OCP - new extractors can be added without modifying existing code.
    """
    
    def __init__(self):
        self._extractors: Dict[TextFormat, Type[TextExtractor]] = {}
        self._config_factories: Dict[TextFormat, Callable[..., TextConfiguration]] = {}
        self._register_default_extractors()
    
    def _register_default_extractors(self) -> None:
        """Register default text extractors."""
        self.register_extractor(
            TextFormat.PDF, 
            PDFTextExtractor,
            PDFConfiguration
        )
        self.register_extractor(
            TextFormat.DOCX, 
            DOCXTextExtractor,
            DOCXConfiguration
        )
        self.register_extractor(
            TextFormat.TXT, 
            PlainTextExtractor,
            PlainTextConfiguration
        )
        self.register_extractor(
            TextFormat.MARKDOWN, 
            PlainTextExtractor,
            PlainTextConfiguration
        )
    
    def register_extractor(
        self, 
        format_type: TextFormat, 
        extractor_class: Type[TextExtractor],
        config_class: Type[TextConfiguration]
    ) -> None:
        """
        Register a new text extractor.
        Enables extension without modification (OCP).
        """
        self._extractors[format_type] = extractor_class
        self._config_factories[format_type] = config_class
    
    def create_extractor(self, format_type: TextFormat) -> TextExtractor:
        """Create text extractor for specific format."""
        if format_type not in self._extractors:
            raise ValueError(f"Unknown text format: {format_type}")
        
        extractor_class = self._extractors[format_type]
        config_class = self._config_factories[format_type]
        
        # Create default configuration
        config = config_class()
        
        return extractor_class(config)
    
    def create_extractor_with_config(
        self, 
        format_type: TextFormat, 
        config: TextConfiguration
    ) -> TextExtractor:
        """Create extractor with custom configuration."""
        if format_type not in self._extractors:
            raise ValueError(f"Unknown text format: {format_type}")
        
        extractor_class = self._extractors[format_type]
        return extractor_class(config)
    
    def create_extractor_with_params(
        self, 
        format_type: TextFormat, 
        **config_params
    ) -> TextExtractor:
        """Create extractor with configuration parameters."""
        if format_type not in self._config_factories:
            raise ValueError(f"Unknown text format: {format_type}")
        
        config_class = self._config_factories[format_type]
        config = config_class(**config_params)
        return self.create_extractor_with_config(format_type, config)
    
    def get_supported_formats(self) -> List[TextFormat]:
        """Get list of supported formats."""
        return list(self._extractors.keys())
    
    def get_extractor_for_mime_type(self, mime_type: str) -> TextExtractor:
        """Get extractor based on MIME type."""
        mime_to_format = {
            "application/pdf": TextFormat.PDF,
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": TextFormat.DOCX,
            "text/plain": TextFormat.TXT,
            "text/markdown": TextFormat.MARKDOWN,
            "text/x-markdown": TextFormat.MARKDOWN
        }
        
        format_type = mime_to_format.get(mime_type)
        if not format_type:
            raise ValueError(f"Unsupported MIME type: {mime_type}")
        
        return self.create_extractor(format_type)


# Global factory instance
_text_factory = ConcreteTextExtractorFactory()


def get_text_extractor_factory() -> TextExtractorFactory:
    """Get the global text extractor factory instance."""
    return _text_factory


def register_text_extractor(
    format_type: TextFormat, 
    extractor_class: Type[TextExtractor],
    config_class: Type[TextConfiguration]
) -> None:
    """
    Register a custom text extractor globally.
    Allows third-party extensions (OCP).
    """
    _text_factory.register_extractor(format_type, extractor_class, config_class)