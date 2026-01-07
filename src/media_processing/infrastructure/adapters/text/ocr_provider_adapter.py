# src/media_processing/infrastructure/adapters/text/ocr_provider_adapter.py
from __future__ import annotations

import asyncio
import structlog
from pathlib import Path

logger = structlog.get_logger(__name__)

class OCRProvider:
    """Extracts text from images or non-text PDFs using Tesseract OCR."""

    async def extract(self, file_path: str) -> str:
        logger.info("ocr_provider.extracting", file_path=file_path)
        path = Path(file_path)
        
        # If it's a PDF, we might need to convert pages to images first
        if path.suffix == ".pdf":
            return await self._ocr_pdf(path)
        
        return await self._ocr_image(path)

    async def _ocr_image(self, path: Path) -> str:
        try:
            import pytesseract
            from PIL import Image
            
            def _run():
                img = Image.open(path)
                # Try Portuguese and English
                return pytesseract.image_to_string(img, lang="por+eng")
            
            return await asyncio.to_thread(_run)
        except Exception as e:
            logger.error("ocr_provider.image_failed", error=str(exc))
            return f"OCR Error: {str(e)}"

    async def _ocr_pdf(self, path: Path) -> str:
        """OCR for PDFs (images inside PDF or scanned PDF)."""
        try:
            import fitz  # PyMuPDF
            import pytesseract
            from PIL import Image
            import io

            def _run():
                text = []
                with fitz.open(path) as doc:
                    for page in doc:
                        # Convert page to image (pixmap)
                        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # 2x zoom for better OCR
                        img_data = pix.tobytes("png")
                        img = Image.open(io.BytesIO(img_data))
                        text.append(pytesseract.image_to_string(img, lang="por+eng"))
                return "\n\n".join(text)

            return await asyncio.to_thread(_run)
        except Exception as e:
            logger.error("ocr_provider.pdf_failed", error=str(e))
            return f"OCR PDF Error: {str(e)}"