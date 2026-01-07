# src/media_processing/infrastructure/adapters/text/text_extractor_adapter.py
from __future__ import annotations

import asyncio
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

class TextExtractor:
    """Extracts text from native formats like txt, docx, pdf (text layer)."""

    async def extract(self, file_path: str, mime_type: str) -> str:
        logger.info(
            "text_extractor.extracting",
            file_path=file_path,
            mime_type=mime_type,
        )
        path = Path(file_path)

        # Simple implementation for .txt and similar
        if mime_type.startswith("text/") or path.suffix in [
            ".txt",
            ".md",
            ".csv",
            ".json",
            ".xml",
        ]:
            return await self._extract_raw_text(path)

        if path.suffix == ".pdf" or mime_type == "application/pdf":
            return await self._extract_pdf(path)

        if path.suffix == ".docx" or mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return await self._extract_docx(path)

        return ""

    async def _extract_raw_text(self, path: Path) -> str:
        try:
            def _read():
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
            return await asyncio.to_thread(_read)
        except Exception as e:
            logger.error("text_extractor.raw_failed", error=str(e))
            raise

    async def _extract_pdf(self, path: Path) -> str:
        try:
            import fitz  # PyMuPDF
            def _read():
                text = []
                with fitz.open(path) as doc:
                    for page in doc:
                        text.append(page.get_text())
                return "\n\n".join(text)
            return await asyncio.to_thread(_read)
        except Exception as e:
            logger.error("text_extractor.pdf_failed", error=str(e))
            return f"Error extracting PDF: {str(e)}"

    async def _extract_docx(self, path: Path) -> str:
        try:
            import docx
            def _read():
                doc = docx.Document(path)
                return "\n".join([para.text for para in doc.paragraphs])
            return await asyncio.to_thread(_read)
        except Exception as e:
            logger.error("text_extractor.docx_failed", error=str(e))
            return f"Error extracting DOCX: {str(e)}"