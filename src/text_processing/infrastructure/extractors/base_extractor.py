# src/text_processing/infrastructure/extractors/base_extractor.py
"""
Base implementation for text extractors - Template Method pattern.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
import magic

from src.text_processing.domain.interfaces import TextExtractor, TextFormat, TextConfiguration


class TextExtractionError(Exception):
    """Base exception for text extraction errors."""
    pass


class BaseTextExtractor(TextExtractor):
    """
    Base text extractor implementing common functionality.
    Follows Template Method pattern and OCP.
    """
    
    def __init__(self, config: TextConfiguration):
        self._config = config
        self._validate_configuration()
    
    def _validate_configuration(self) -> None:
        """Validate extractor configuration."""
        if not self._config.validate_config():
            raise TextExtractionError("Invalid text extraction configuration")
    
    async def extract_text(self, file_content: bytes, format_type: TextFormat) -> str:
        """Template method for text extraction."""
        try:
            # Pre-extraction hook
            await self._pre_extract(file_content, format_type)
            
            # Validate file content
            self._validate_file_content(file_content)
            
            # Check format support
            if format_type not in self.supported_formats:
                raise TextExtractionError(f"Format {format_type} not supported by this extractor")
            
            # Actual extraction (implemented by subclasses)
            raw_text = await self._do_extract(file_content, format_type)
            
            # Post-processing
            processed_text = await self._post_process_text(raw_text)
            
            # Post-extraction hook
            await self._post_extract(file_content, format_type, processed_text)
            
            return processed_text
            
        except Exception as e:
            await self._handle_extraction_error(file_content, format_type, e)
            raise TextExtractionError(f"Text extraction failed") from e
    
    async def validate_format(self, file_content: bytes, format_type: TextFormat) -> bool:
        """Validate file format using magic numbers and format-specific checks."""
        try:
            # Check file size
            if len(file_content) > self._config.get_max_file_size():
                return False
            
            # Use python-magic for MIME type detection
            mime_type = magic.from_buffer(file_content, mime=True)
            
            # Format-specific validation
            return await self._validate_format_specific(file_content, format_type, mime_type)
            
        except Exception:
            return False
    
    def _validate_file_content(self, file_content: bytes) -> None:
        """Validate file content."""
        if not file_content:
            raise TextExtractionError("File content is empty")
        
        max_size = self._config.get_max_file_size()
        if len(file_content) > max_size:
            raise TextExtractionError(
                f"File size {len(file_content)} exceeds maximum {max_size}"
            )
    
    # Abstract methods to be implemented by subclasses
    @abstractmethod
    async def _do_extract(self, file_content: bytes, format_type: TextFormat) -> str:
        """Actual extraction implementation."""
        pass
    
    @abstractmethod
    async def _validate_format_specific(
        self, 
        file_content: bytes, 
        format_type: TextFormat, 
        mime_type: str
    ) -> bool:
        """Format-specific validation."""
        pass
    
    # Hook methods (can be overridden by subclasses)
    async def _pre_extract(self, file_content: bytes, format_type: TextFormat) -> None:
        """Hook called before extraction."""
        pass
    
    async def _post_extract(
        self, 
        file_content: bytes, 
        format_type: TextFormat, 
        extracted_text: str
    ) -> None:
        """Hook called after successful extraction."""
        pass
    
    async def _post_process_text(self, text: str) -> str:
        """Post-process extracted text."""
        # Default implementation: basic cleaning
        return text.strip()
    
    async def _handle_extraction_error(
        self, 
        file_content: bytes, 
        format_type: TextFormat, 
        error: Exception
    ) -> None:
        """Handle extraction errors."""
        pass
    
    def _get_mime_type_mapping(self) -> Dict[TextFormat, List[str]]:
        """Get mapping of text formats to MIME types."""
        return {
            TextFormat.PDF: ["application/pdf"],
            TextFormat.DOCX: [
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ],
            TextFormat.TXT: ["text/plain"],
            TextFormat.RTF: ["application/rtf", "text/rtf"],
            TextFormat.HTML: ["text/html"],
            TextFormat.MARKDOWN: ["text/markdown", "text/x-markdown"]
        }
    
    async def _get_extractor_capabilities(self) -> Dict[str, Any]:
        """Get extractor-specific capabilities."""
        return {
            "supported_formats": [fmt.value for fmt in self.supported_formats],
            "max_file_size": self._config.get_max_file_size()
        }