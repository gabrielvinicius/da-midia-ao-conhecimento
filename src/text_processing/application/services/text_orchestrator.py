# src/text_processing/application/services/text_orchestrator.py
"""
Text processing orchestrator implementation - DIP compliance.
"""
from typing import Optional
import structlog
import magic

from src.text_processing.domain.interfaces import (
    TextProcessingOrchestrator,
    TextExtractorFactory,
    TextFormat
)
from src.text_processing.domain.services.text_coordinator import TextCoordinator

logger = structlog.get_logger(__name__)


class TextProcessingOrchestratorImpl(TextProcessingOrchestrator):
    """
    High-level orchestrator for text processing operations.
    Follows DIP - depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        extractor_factory: TextExtractorFactory,
        coordinator: TextCoordinator
    ):
        self._extractor_factory = extractor_factory
        self._coordinator = coordinator
        self._processing_status = {}  # In real implementation, use repository
    
    async def process_text_file(
        self, 
        media_id: str, 
        file_content: bytes,
        format_type: TextFormat,
        user_id: str
    ) -> str:
        """Process complete text extraction workflow."""
        logger.info(
            "text_processing.orchestrator.start",
            media_id=media_id,
            format_type=format_type.value,
            user_id=user_id,
            file_size=len(file_content)
        )
        
        # Check if already processing
        if await self._is_processing(media_id):
            logger.warning(
                "text_processing.orchestrator.already_processing",
                media_id=media_id
            )
            raise ValueError(f"Text processing already in progress for media {media_id}")
        
        # Mark as processing
        self._processing_status[media_id] = "processing"
        
        try:
            # Detect format if not provided or validate provided format
            detected_format = await self._detect_and_validate_format(
                file_content, format_type
            )
            
            # Process text using coordinator
            extracted_text = await self._coordinator.extract_and_process_text(
                media_id=media_id,
                file_content=file_content,
                format_type=detected_format,
                user_id=user_id
            )
            
            # Mark as completed
            self._processing_status[media_id] = "completed"
            
            logger.info(
                "text_processing.orchestrator.completed",
                media_id=media_id,
                text_length=len(extracted_text)
            )
            
            return extracted_text
            
        except Exception as e:
            # Mark as failed
            self._processing_status[media_id] = "failed"
            
            logger.error(
                "text_processing.orchestrator.failed",
                media_id=media_id,
                error=str(e)
            )
            
            raise
    
    async def get_processing_status(self, media_id: str) -> Optional[str]:
        """Get text processing status."""
        return self._processing_status.get(media_id)
    
    async def retry_failed_processing(
        self,
        media_id: str,
        file_content: bytes,
        format_type: TextFormat,
        user_id: str
    ) -> str:
        """Retry failed text processing."""
        logger.info(
            "text_processing.orchestrator.retry",
            media_id=media_id,
            format_type=format_type.value
        )
        
        # Reset status
        if media_id in self._processing_status:
            del self._processing_status[media_id]
        
        # Process again
        return await self.process_text_file(
            media_id=media_id,
            file_content=file_content,
            format_type=format_type,
            user_id=user_id
        )
    
    async def _detect_and_validate_format(
        self, 
        file_content: bytes, 
        expected_format: TextFormat
    ) -> TextFormat:
        """Detect and validate file format."""
        try:
            # Get MIME type
            mime_type = magic.from_buffer(file_content, mime=True)
            
            # Create mapping of MIME types to formats
            mime_to_format = {
                "application/pdf": TextFormat.PDF,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document": TextFormat.DOCX,
                "text/plain": TextFormat.TXT,
                "text/markdown": TextFormat.MARKDOWN,
                "text/x-markdown": TextFormat.MARKDOWN
            }
            
            detected_format = mime_to_format.get(mime_type)
            
            # If we detected a format
            if detected_format:
                # Check if it matches expected format
                if detected_format != expected_format:
                    logger.warning(
                        "text_processing.format_mismatch",
                        expected=expected_format.value,
                        detected=detected_format.value,
                        mime_type=mime_type
                    )
                    # Use detected format instead
                    return detected_format
                
                return detected_format
            
            # If no format detected, try to use expected format
            if expected_format in self._extractor_factory.get_supported_formats():
                logger.warning(
                    "text_processing.format_not_detected",
                    expected_format=expected_format.value,
                    mime_type=mime_type
                )
                return expected_format
            
            # Format not supported
            raise ValueError(
                f"Unsupported file format. MIME type: {mime_type}, "
                f"Expected: {expected_format.value}"
            )
            
        except Exception as e:
            logger.error(
                "text_processing.format_detection_failed",
                expected_format=expected_format.value,
                error=str(e)
            )
            
            # Fallback to expected format if detection fails
            if expected_format in self._extractor_factory.get_supported_formats():
                return expected_format
            
            raise ValueError(f"Format detection failed and format not supported: {e}")
    
    async def _is_processing(self, media_id: str) -> bool:
        """Check if text processing is currently in progress."""
        status = self._processing_status.get(media_id)
        return status == "processing"
    
    async def get_supported_formats(self) -> list[TextFormat]:
        """Get list of supported text formats."""
        return self._extractor_factory.get_supported_formats()
    
    async def validate_file_format(
        self, 
        file_content: bytes, 
        expected_format: TextFormat
    ) -> bool:
        """Validate if file content matches expected format."""
        try:
            await self._detect_and_validate_format(file_content, expected_format)
            return True
        except Exception:
            return False