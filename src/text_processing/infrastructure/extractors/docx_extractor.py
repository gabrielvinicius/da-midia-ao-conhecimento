# src/text_processing/infrastructure/extractors/docx_extractor.py
"""
DOCX text extractor - OCP and SRP compliance.
"""
import io
from typing import List, Dict, Any
from docx import Document

from src.text_processing.domain.interfaces import TextFormat, TextConfiguration
from src.text_processing.infrastructure.extractors.base_extractor import BaseTextExtractor, TextExtractionError


class DOCXConfiguration(TextConfiguration):
    """Configuration for DOCX text extraction - SRP compliance."""
    
    def __init__(
        self,
        max_file_size: int = 30 * 1024 * 1024,  # 30MB
        extract_tables: bool = True,
        extract_headers_footers: bool = True,
        preserve_formatting: bool = False
    ):
        self.max_file_size = max_file_size
        self.extract_tables = extract_tables
        self.extract_headers_footers = extract_headers_footers
        self.preserve_formatting = preserve_formatting
    
    def get_config(self) -> Dict[str, Any]:
        """Get configuration dictionary."""
        return {
            "max_file_size": self.max_file_size,
            "extract_tables": self.extract_tables,
            "extract_headers_footers": self.extract_headers_footers,
            "preserve_formatting": self.preserve_formatting
        }
    
    def validate_config(self) -> bool:
        """Validate configuration."""
        return self.max_file_size > 0
    
    def get_max_file_size(self) -> int:
        """Get maximum file size in bytes."""
        return self.max_file_size
    
    def get_supported_formats(self) -> List[TextFormat]:
        """Get supported text formats."""
        return [TextFormat.DOCX]


class DOCXTextExtractor(BaseTextExtractor):
    """
    DOCX text extractor using python-docx.
    Follows OCP - can be extended without modification.
    """
    
    def __init__(self, config: DOCXConfiguration):
        super().__init__(config)
        self._config = config
    
    @property
    def supported_formats(self) -> List[TextFormat]:
        """Get supported formats."""
        return [TextFormat.DOCX]
    
    async def _do_extract(self, file_content: bytes, format_type: TextFormat) -> str:
        """Extract text from DOCX using python-docx."""
        try:
            # Open DOCX from bytes
            doc = Document(io.BytesIO(file_content))
            
            text_parts = []
            
            # Extract headers if configured
            if self._config.extract_headers_footers:
                headers = self._extract_headers_footers(doc)
                if headers:
                    text_parts.append(headers)
            
            # Extract main document text
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    if self._config.preserve_formatting:
                        formatted_text = self._extract_formatted_text(paragraph)
                        text_parts.append(formatted_text)
                    else:
                        text_parts.append(paragraph.text)
            
            # Extract tables if configured
            if self._config.extract_tables:
                for table in doc.tables:
                    table_text = self._extract_table_text(table)
                    if table_text:
                        text_parts.append(f"\n[TABLE]\n{table_text}\n[/TABLE]\n")
            
            return "\n".join(text_parts)
            
        except Exception as e:
            raise TextExtractionError(f"DOCX extraction failed: {e}") from e
    
    async def _validate_format_specific(
        self, 
        file_content: bytes, 
        format_type: TextFormat, 
        mime_type: str
    ) -> bool:
        """Validate DOCX format."""
        expected_mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if mime_type != expected_mime:
            return False
        
        # Check ZIP magic bytes (DOCX is a ZIP file)
        if not file_content.startswith(b'PK'):
            return False
        
        # Try to open with python-docx
        try:
            doc = Document(io.BytesIO(file_content))
            return True
        except Exception:
            return False
    
    def _extract_headers_footers(self, doc: Document) -> str:
        """Extract headers and footers from document."""
        text_parts = []
        
        try:
            # Extract from all sections
            for section in doc.sections:
                # Headers
                if section.header:
                    for paragraph in section.header.paragraphs:
                        if paragraph.text.strip():
                            text_parts.append(f"[HEADER] {paragraph.text}")
                
                # Footers
                if section.footer:
                    for paragraph in section.footer.paragraphs:
                        if paragraph.text.strip():
                            text_parts.append(f"[FOOTER] {paragraph.text}")
        except Exception:
            # If header/footer extraction fails, continue without them
            pass
        
        return "\n".join(text_parts)
    
    def _extract_formatted_text(self, paragraph) -> str:
        """Extract text with basic formatting information."""
        text_parts = []
        
        for run in paragraph.runs:
            text = run.text
            if text.strip():
                # Add formatting markers
                if run.bold:
                    text = f"**{text}**"
                if run.italic:
                    text = f"*{text}*"
                text_parts.append(text)
        
        return "".join(text_parts)
    
    def _extract_table_text(self, table) -> str:
        """Extract text from DOCX table."""
        rows = []
        
        for row in table.rows:
            cells = []
            for cell in row.cells:
                # Get text from all paragraphs in cell
                cell_text = " ".join(
                    paragraph.text.strip() 
                    for paragraph in cell.paragraphs 
                    if paragraph.text.strip()
                )
                cells.append(cell_text)
            
            if any(cell.strip() for cell in cells):  # Skip empty rows
                rows.append(" | ".join(cells))
        
        return "\n".join(rows)
    
    async def _post_process_text(self, text: str) -> str:
        """Post-process DOCX extracted text."""
        # Basic cleaning
        text = await super()._post_process_text(text)
        
        # DOCX-specific cleaning
        text = self._clean_docx_artifacts(text)
        
        return text
    
    def _clean_docx_artifacts(self, text: str) -> str:
        """Clean DOCX-specific artifacts."""
        import re
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Clean up line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Remove empty formatting markers
        text = re.sub(r'\*\*\s*\*\*', '', text)
        text = re.sub(r'\*\s*\*', '', text)
        
        return text.strip()
    
    async def _get_extractor_capabilities(self) -> Dict[str, Any]:
        """Get DOCX extractor capabilities."""
        base_capabilities = await super()._get_extractor_capabilities()
        
        docx_capabilities = {
            "extract_tables": self._config.extract_tables,
            "extract_headers_footers": self._config.extract_headers_footers,
            "preserve_formatting": self._config.preserve_formatting,
            "supports_images": False,  # Could be added later
            "supports_comments": False  # Could be added later
        }
        
        return {**base_capabilities, **docx_capabilities}