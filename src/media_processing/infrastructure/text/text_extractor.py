import structlog
from pathlib import Path

logger = structlog.get_logger(__name__)

class TextExtractor:
    """Extracts text from native formats like txt, docx, pdf (text layer)."""
    
    async def extract(self, file_path: str, mime_type: str) -> str:
        logger.info("text_extractor.extracting", file_path=file_path, mime_type=mime_type)
        path = Path(file_path)
        
        # Simple implementation for .txt and similar
        if mime_type.startswith("text/") or path.suffix in [".txt", ".md", ".csv", ".json", ".xml"]:
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            except Exception as e:
                logger.error("text_extractor.failed", error=str(e))
                raise

        # Stub for PDF/DOCX
        if path.suffix == ".pdf":
            # Real impl would use pypdf or pdfplumber
            return "PDF extraction stub: content not extracted (install pdfplumber)"
            
        if path.suffix == ".docx":
            # Real impl would use python-docx
            return "DOCX extraction stub: content not extracted (install python-docx)"

        return ""
