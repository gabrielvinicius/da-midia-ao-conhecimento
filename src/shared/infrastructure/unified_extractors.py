"""
Unified text extractors - eliminating extractor duplication
"""
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import structlog
from pathlib import Path
import io

logger = structlog.get_logger(__name__)

class ExtractionResult:
    """Unified extraction result"""
    def __init__(self, text: str, metadata: Dict[str, Any] = None):
        self.text = text
        self.metadata = metadata or {}
        self.success = bool(text.strip())

class UnifiedTextExtractor:
    """Single text extractor for all file types - eliminating extractor duplication"""
    
    def __init__(self):
        self.logger = logger.bind(component="text_extractor")
        self._supported_types = {
            '.txt': self._extract_plain_text,
            '.pdf': self._extract_pdf,
            '.docx': self._extract_docx,
            '.doc': self._extract_doc,
            '.html': self._extract_html,
            '.htm': self._extract_html,
            '.md': self._extract_markdown,
            '.rtf': self._extract_rtf
        }
    
    async def extract(self, file_data: bytes, filename: str) -> ExtractionResult:
        """Extract text from file based on extension"""
        try:
            file_ext = Path(filename).suffix.lower()
            
            if file_ext not in self._supported_types:
                self.logger.warning("Unsupported file type", 
                                  filename=filename, extension=file_ext)
                return ExtractionResult("", {"error": f"Unsupported file type: {file_ext}"})
            
            self.logger.debug("Starting text extraction", 
                            filename=filename, extension=file_ext, size=len(file_data))
            
            # Get appropriate extractor method
            extractor_method = self._supported_types[file_ext]
            
            # Extract text
            text = await extractor_method(file_data, filename)
            
            # Validate and clean text
            cleaned_text = self._clean_text(text)
            
            result = ExtractionResult(
                text=cleaned_text,
                metadata={
                    "filename": filename,
                    "file_type": file_ext,
                    "original_size": len(file_data),
                    "extracted_length": len(cleaned_text),
                    "extraction_method": extractor_method.__name__
                }
            )
            
            self.logger.info("Text extraction completed", 
                           filename=filename, 
                           text_length=len(cleaned_text),
                           success=result.success)
            
            return result
            
        except Exception as e:
            self.logger.error("Text extraction failed", 
                            filename=filename, error=str(e))
            return ExtractionResult("", {"error": str(e)})
    
    async def _extract_plain_text(self, file_data: bytes, filename: str) -> str:
        """Extract text from plain text files"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    return file_data.decode(encoding)
                except UnicodeDecodeError:
                    continue
            
            # If all encodings fail, decode with errors='ignore'
            return file_data.decode('utf-8', errors='ignore')
            
        except Exception as e:
            self.logger.error("Failed to extract plain text", error=str(e))
            return ""
    
    async def _extract_pdf(self, file_data: bytes, filename: str) -> str:
        """Extract text from PDF files"""
        try:
            # Try importing PyPDF2 or pdfplumber
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(io.BytesIO(file_data))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
            except ImportError:
                try:
                    import pdfplumber
                    with pdfplumber.open(io.BytesIO(file_data)) as pdf:
                        text = ""
                        for page in pdf.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                        return text
                except ImportError:
                    self.logger.warning("No PDF library available (PyPDF2 or pdfplumber)")
                    return ""
        except Exception as e:
            self.logger.error("Failed to extract PDF text", error=str(e))
            return ""
    
    async def _extract_docx(self, file_data: bytes, filename: str) -> str:
        """Extract text from DOCX files"""
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_data))
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except ImportError:
            self.logger.warning("python-docx not available")
            return ""
        except Exception as e:
            self.logger.error("Failed to extract DOCX text", error=str(e))
            return ""
    
    async def _extract_doc(self, file_data: bytes, filename: str) -> str:
        """Extract text from DOC files"""
        try:
            # DOC files are more complex, would need additional libraries
            self.logger.warning("DOC file extraction not fully implemented")
            return ""
        except Exception as e:
            self.logger.error("Failed to extract DOC text", error=str(e))
            return ""
    
    async def _extract_html(self, file_data: bytes, filename: str) -> str:
        """Extract text from HTML files"""
        try:
            from bs4 import BeautifulSoup
            html_content = file_data.decode('utf-8', errors='ignore')
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            return soup.get_text()
        except ImportError:
            self.logger.warning("BeautifulSoup not available for HTML extraction")
            # Fallback: simple HTML tag removal
            html_content = file_data.decode('utf-8', errors='ignore')
            import re
            clean = re.compile('<.*?>')
            return re.sub(clean, '', html_content)
        except Exception as e:
            self.logger.error("Failed to extract HTML text", error=str(e))
            return ""
    
    async def _extract_markdown(self, file_data: bytes, filename: str) -> str:
        """Extract text from Markdown files"""
        try:
            # For markdown, we can just remove the markdown syntax
            text = file_data.decode('utf-8', errors='ignore')
            
            # Simple markdown cleanup
            import re
            # Remove headers
            text = re.sub(r'^#+\s*', '', text, flags=re.MULTILINE)
            # Remove links
            text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
            # Remove bold/italic
            text = re.sub(r'\*\*([^\*]+)\*\*', r'\1', text)
            text = re.sub(r'\*([^\*]+)\*', r'\1', text)
            # Remove code blocks
            text = re.sub(r'```[^`]*```', '', text, flags=re.DOTALL)
            text = re.sub(r'`([^`]+)`', r'\1', text)
            
            return text
        except Exception as e:
            self.logger.error("Failed to extract Markdown text", error=str(e))
            return ""
    
    async def _extract_rtf(self, file_data: bytes, filename: str) -> str:
        """Extract text from RTF files"""
        try:
            # RTF is complex, would need a specialized library
            self.logger.warning("RTF file extraction not fully implemented")
            return ""
        except Exception as e:
            self.logger.error("Failed to extract RTF text", error=str(e))
            return ""
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text
    
    def get_supported_types(self) -> List[str]:
        """Get list of supported file types"""
        return list(self._supported_types.keys())
    
    def is_supported(self, filename: str) -> bool:
        """Check if file type is supported"""
        file_ext = Path(filename).suffix.lower()
        return file_ext in self._supported_types

# Global extractor instance
text_extractor = UnifiedTextExtractor()

# Convenience function
async def extract_text_from_file(file_data: bytes, filename: str) -> ExtractionResult:
    """Extract text from file"""
    return await text_extractor.extract(file_data, filename)