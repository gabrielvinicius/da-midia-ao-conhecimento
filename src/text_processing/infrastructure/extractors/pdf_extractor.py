# src/text_processing/infrastructure/extractors/pdf_extractor.py
"""
PDF text extractor - OCP and SRP compliance.
"""
import io
from typing import List, Dict, Any
import fitz  # PyMuPDF

from src.text_processing.domain.interfaces import TextFormat, TextConfiguration
from src.text_processing.infrastructure.extractors.base_extractor import BaseTextExtractor


class PDFConfiguration(TextConfiguration):
    """Configuration for PDF text extraction - SRP compliance."""
    
    def __init__(
        self,
        max_file_size: int = 50 * 1024 * 1024,  # 50MB
        extract_images: bool = False,
        extract_tables: bool = False,
        preserve_layout: bool = False
    ):
        self.max_file_size = max_file_size
        self.extract_images = extract_images
        self.extract_tables = extract_tables
        self.preserve_layout = preserve_layout
    
    def get_config(self) -> Dict[str, Any]:
        """Get configuration dictionary."""
        return {
            "max_file_size": self.max_file_size,
            "extract_images": self.extract_images,
            "extract_tables": self.extract_tables,
            "preserve_layout": self.preserve_layout
        }
    
    def validate_config(self) -> bool:
        """Validate configuration."""
        return self.max_file_size > 0
    
    def get_max_file_size(self) -> int:
        """Get maximum file size in bytes."""
        return self.max_file_size
    
    def get_supported_formats(self) -> List[TextFormat]:
        """Get supported text formats."""
        return [TextFormat.PDF]


class PDFTextExtractor(BaseTextExtractor):
    """
    PDF text extractor using PyMuPDF.
    Follows OCP - can be extended without modification.
    """
    
    def __init__(self, config: PDFConfiguration):
        super().__init__(config)
        self._config = config
    
    @property
    def supported_formats(self) -> List[TextFormat]:
        """Get supported formats."""
        return [TextFormat.PDF]
    
    async def _do_extract(self, file_content: bytes, format_type: TextFormat) -> str:
        """Extract text from PDF using PyMuPDF."""
        try:
            # Open PDF from bytes
            doc = fitz.open(stream=io.BytesIO(file_content), filetype="pdf")
            
            # Extract text from all pages
            text_parts = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                if self._config.preserve_layout:
                    # Extract with layout preservation
                    page_text = page.get_text("dict")
                    text_parts.append(self._process_layout_dict(page_text))
                else:
                    # Simple text extraction
                    page_text = page.get_text()
                    text_parts.append(page_text)
                
                # Extract tables if configured
                if self._config.extract_tables:
                    tables = self._extract_tables_from_page(page)
                    text_parts.extend(tables)
            
            doc.close()
            
            # Combine all text
            full_text = "\n\n".join(text_parts)
            
            return full_text
            
        except Exception as e:
            raise TextExtractionError(f"PDF extraction failed: {e}") from e
    
    async def _validate_format_specific(
        self, 
        file_content: bytes, 
        format_type: TextFormat, 
        mime_type: str
    ) -> bool:
        """Validate PDF format."""
        # Check MIME type
        if mime_type != "application/pdf":
            return False
        
        # Check PDF magic bytes
        if not file_content.startswith(b'%PDF-'):
            return False
        
        # Try to open with PyMuPDF
        try:
            doc = fitz.open(stream=io.BytesIO(file_content), filetype="pdf")
            is_valid = doc.page_count > 0
            doc.close()
            return is_valid
        except Exception:
            return False
    
    def _process_layout_dict(self, page_dict: dict) -> str:
        """Process PyMuPDF text dictionary to preserve layout."""
        text_parts = []
        
        for block in page_dict.get("blocks", []):
            if "lines" in block:  # Text block
                for line in block["lines"]:
                    line_text = ""
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                    text_parts.append(line_text)
        
        return "\n".join(text_parts)
    
    def _extract_tables_from_page(self, page) -> List[str]:
        """Extract tables from PDF page."""
        tables = []
        try:
            # Find tables using PyMuPDF
            tabs = page.find_tables()
            for tab in tabs:
                table_data = tab.extract()
                if table_data:
                    # Convert table to text representation
                    table_text = self._table_to_text(table_data)
                    tables.append(f"\n[TABLE]\n{table_text}\n[/TABLE]\n")
        except Exception:
            # If table extraction fails, continue without tables
            pass
        
        return tables
    
    def _table_to_text(self, table_data: List[List[str]]) -> str:
        """Convert table data to text representation."""
        if not table_data:
            return ""
        
        # Simple table formatting
        text_rows = []
        for row in table_data:
            # Clean and join cells
            cleaned_row = [str(cell).strip() if cell else "" for cell in row]
            text_rows.append(" | ".join(cleaned_row))
        
        return "\n".join(text_rows)
    
    async def _post_process_text(self, text: str) -> str:
        """Post-process PDF extracted text."""
        # Basic cleaning
        text = super()._post_process_text(text)
        
        # PDF-specific cleaning
        text = self._clean_pdf_artifacts(text)
        
        return text
    
    def _clean_pdf_artifacts(self, text: str) -> str:
        """Clean PDF-specific artifacts."""
        # Remove excessive whitespace
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove lines with only whitespace or special characters
            cleaned_line = line.strip()
            if cleaned_line and len(cleaned_line) > 1:
                cleaned_lines.append(cleaned_line)
        
        # Rejoin with single newlines
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Remove multiple consecutive newlines
        import re
        cleaned_text = re.sub(r'\n{3,}', '\n\n', cleaned_text)
        
        return cleaned_text
    
    async def _get_extractor_capabilities(self) -> Dict[str, Any]:
        """Get PDF extractor capabilities."""
        base_capabilities = await super()._get_extractor_capabilities()
        
        pdf_capabilities = {
            "extract_images": self._config.extract_images,
            "extract_tables": self._config.extract_tables,
            "preserve_layout": self._config.preserve_layout,
            "supports_password_protected": False,  # Could be added later
            "supports_scanned_pdfs": False  # Would need OCR
        }
        
        return {**base_capabilities, **pdf_capabilities}