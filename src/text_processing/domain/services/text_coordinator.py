# src/text_processing/domain/services/text_coordinator.py
"""
Domain service for coordinating text processing operations - SRP compliance.
"""
from datetime import datetime
from typing import Optional

from src.text_processing.domain.interfaces import (
    TextExtractor,
    TextValidator,
    TextProcessor,
    TextOperationLogger,
    TextMetrics,
    TextNotificationService,
    TextFormat
)


class TextProcessingError(Exception):
    """Domain exception for text processing errors."""
    pass


class TextCoordinator:
    """
    Domain service that coordinates text processing operations with logging and metrics.
    Follows SRP by focusing only on coordination logic.
    """
    
    def __init__(
        self,
        extractor: TextExtractor,
        validator: TextValidator,
        processor: TextProcessor,
        logger: TextOperationLogger,
        metrics: TextMetrics,
        notification_service: TextNotificationService
    ):
        self._extractor = extractor
        self._validator = validator
        self._processor = processor
        self._logger = logger
        self._metrics = metrics
        self._notification_service = notification_service
    
    async def extract_and_process_text(
        self, 
        media_id: str,
        file_content: bytes,
        format_type: TextFormat,
        user_id: str
    ) -> str:
        """Extract and process text with logging and metrics."""
        start_time = datetime.utcnow()
        success = False
        error = None
        file_size = len(file_content)
        text_length = 0
        
        try:
            # Notify processing started
            await self._notification_service.notify_started(media_id, user_id)
            
            # Validate format
            if not await self._extractor.validate_format(file_content, format_type):
                raise TextProcessingError(f"Invalid file format: {format_type}")
            
            # Extract text
            raw_text = await self._extractor.extract_text(file_content, format_type)
            
            if not raw_text or not raw_text.strip():
                raise TextProcessingError("No text content found in file")
            
            # Validate extracted text
            if not await self._validator.validate_content(raw_text):
                raise TextProcessingError("Extracted text failed validation")
            
            # Process text (clean and normalize)
            processed_text = await self._processor.clean_text(raw_text)
            text_length = len(processed_text)
            
            # Notify completion
            await self._notification_service.notify_completed(
                media_id, user_id, text_length
            )
            
            success = True
            return processed_text
            
        except Exception as e:
            error = e
            success = False
            
            # Notify failure
            await self._notification_service.notify_failed(
                media_id, user_id, str(e)
            )
            
            raise TextProcessingError(
                f"Failed to process text for media {media_id}: {e}"
            ) from e
            
        finally:
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Log operation
            await self._logger.log_operation(
                operation="extract_text",
                media_id=media_id,
                format_type=format_type.value,
                success=success,
                duration=duration,
                text_length=text_length if success else None,
                error=error
            )
            
            # Record metrics
            await self._metrics.record_operation(
                operation="extract_text",
                format_type=format_type.value,
                duration=duration,
                success=success,
                file_size=file_size,
                text_length=text_length
            )
    
    async def get_text_metadata(self, text: str) -> dict:
        """Get text metadata with error handling."""
        try:
            metadata = await self._processor.extract_metadata(text)
            stats = await self._validator.get_content_stats(text)
            language = await self._validator.detect_language(text)
            
            return {
                **metadata,
                "stats": stats,
                "language": language
            }
        except Exception as e:
            await self._logger.log_operation(
                operation="extract_metadata",
                media_id="unknown",
                format_type="unknown",
                success=False,
                duration=0.0,
                error=e
            )
            return {}