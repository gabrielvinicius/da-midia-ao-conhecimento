# src/text_processing/infrastructure/extractors/plain_text_extractor.py
"""
Plain text extractor - OCP and SRP compliance.
"""
import chardet
from typing import List, Dict, Any

from src.text_processing.domain.interfaces import TextFormat, TextConfiguration
from src.text_processing.infrastructure.extractors.base_extractor import BaseTextExtractor, TextExtractionError


class PlainTextConfiguration(TextConfiguration):
    """Configuration for plain text extraction - SRP compliance."""
    
    def __init__(
        self,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        encoding: str = "auto",
        preserve_line_breaks: bool = True,
        normalize_whitespace: bool = True
    ):
        self.max_file_size = max_file_size
        self.encoding = encoding
        self.preserve_line_breaks = preserve_line_breaks
        self.normalize_whitespace = normalize_whitespace
    
    def get_config(self) -> Dict[str, Any]:
        """Get configuration dictionary."""
        return {
            "max_file_size": self.max_file_size,
            "encoding": self.encoding,
            "preserve_line_breaks": self.preserve_line_breaks,
            "normalize_whitespace": self.normalize_whitespace
        }
    
    def validate_config(self) -> bool:
        """Validate configuration."""
        return self.max_file_size > 0
    
    def get_max_file_size(self) -> int:
        """Get maximum file size in bytes."""
        return self.max_file_size
    
    def get_supported_formats(self) -> List[TextFormat]:
        """Get supported text formats."""
        return [TextFormat.TXT, TextFormat.MARKDOWN]


class PlainTextExtractor(BaseTextExtractor):
    """
    Plain text extractor for TXT and Markdown files.
    Follows OCP - can be extended without modification.
    """
    
    def __init__(self, config: PlainTextConfiguration):
        super().__init__(config)
        self._config = config
    
    @property
    def supported_formats(self) -> List[TextFormat]:
        """Get supported formats."""
        return [TextFormat.TXT, TextFormat.MARKDOWN]
    
    async def _do_extract(self, file_content: bytes, format_type: TextFormat) -> str:
        """Extract text from plain text files."""
        try:
            # Detect encoding
            encoding = self._detect_encoding(file_content)
            
            # Decode text
            text = file_content.decode(encoding)
            
            # Format-specific processing
            if format_type == TextFormat.MARKDOWN:
                text = self._process_markdown(text)
            
            return text
            
        except Exception as e:
            raise TextExtractionError(f"Plain text extraction failed: {e}") from e
    
    async def _validate_format_specific(
        self, 
        file_content: bytes, 
        format_type: TextFormat, 
        mime_type: str
    ) -> bool:
        """Validate plain text format."""
        expected_mimes = {
            TextFormat.TXT: ["text/plain"],
            TextFormat.MARKDOWN: ["text/markdown", "text/x-markdown", "text/plain"]
        }
        
        if mime_type not in expected_mimes.get(format_type, []):
            return False
        
        # Try to decode as text
        try:
            encoding = self._detect_encoding(file_content)
            file_content.decode(encoding)
            return True
        except Exception:
            return False
    
    def _detect_encoding(self, file_content: bytes) -> str:
        """Detect file encoding."""
        if self._config.encoding != "auto":
            return self._config.encoding
        
        # Use chardet for automatic detection
        detection = chardet.detect(file_content)
        encoding = detection.get('encoding', 'utf-8')
        
        # Fallback to common encodings
        if not encoding or detection.get('confidence', 0) < 0.7:
            # Try common encodings
            for fallback_encoding in ['utf-8', 'utf-16', 'latin-1', 'cp1252']:
                try:
                    file_content.decode(fallback_encoding)
                    return fallback_encoding
                except UnicodeDecodeError:
                    continue
            
            # Last resort
            encoding = 'utf-8'
        
        return encoding
    
    def _process_markdown(self, text: str) -> str:
        """Process Markdown text to extract plain text content."""
        import re
        
        # Remove Markdown syntax while preserving content
        # Headers
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        
        # Bold and italic
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'\*(.+?)\*', r'\1', text)
        text = re.sub(r'__(.+?)__', r'\1', text)
        text = re.sub(r'_(.+?)_', r'\1', text)
        
        # Links
        text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
        
        # Images
        text = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'[Image: \1]', text)
        
        # Code blocks
        text = re.sub(r'```[\s\S]*?```', '[Code Block]', text)
        text = re.sub(r'`([^`]+)`', r'\1', text)
        
        # Lists
        text = re.sub(r'^\s*[-\*\+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\d+\.\s+', '', text, flags=re.MULTILINE)
        
        # Blockquotes
        text = re.sub(r'^>\s*', '', text, flags=re.MULTILINE)
        
        # Horizontal rules
        text = re.sub(r'^[-\*_]{3,}$', '', text, flags=re.MULTILINE)
        
        return text
    
    async def _post_process_text(self, text: str) -> str:
        """Post-process plain text."""
        # Basic cleaning
        text = await super()._post_process_text(text)
        
        # Plain text specific processing
        if self._config.normalize_whitespace:
            text = self._normalize_whitespace(text)
        
        if not self._config.preserve_line_breaks:
            text = self._remove_line_breaks(text)
        
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace in text."""
        import re
        
        # Replace multiple spaces with single space
        text = re.sub(r' +', ' ', text)
        
        # Replace multiple line breaks with double line break
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove trailing spaces from lines
        text = re.sub(r' +\n', '\n', text)
        
        return text
    
    def _remove_line_breaks(self, text: str) -> str:
        """Remove line breaks for continuous text."""
        import re
        
        # Replace single line breaks with spaces, keep double line breaks
        text = re.sub(r'(?<!\n)\n(?!\n)', ' ', text)
        
        # Clean up any resulting multiple spaces
        text = re.sub(r' +', ' ', text)
        
        return text
    
    async def _get_extractor_capabilities(self) -> Dict[str, Any]:
        """Get plain text extractor capabilities."""
        base_capabilities = await super()._get_extractor_capabilities()
        
        text_capabilities = {
            "encoding_detection": self._config.encoding == "auto",
            "preserve_line_breaks": self._config.preserve_line_breaks,
            "normalize_whitespace": self._config.normalize_whitespace,
            "supports_markdown": TextFormat.MARKDOWN in self.supported_formats,
            "supports_encoding": ["utf-8", "utf-16", "latin-1", "cp1252"]
        }
        
        return {**base_capabilities, **text_capabilities}