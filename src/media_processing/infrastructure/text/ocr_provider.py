import structlog

logger = structlog.get_logger(__name__)

class OCRProvider:
    """Extracts text from images using OCR."""
    
    async def extract(self, file_path: str) -> str:
        logger.info("ocr_provider.extracting", file_path=file_path)
        # Stub implementation
        return "OCR Extraction Stub: [Image Content]"
