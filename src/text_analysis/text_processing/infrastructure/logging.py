# src/text_processing/infrastructure/logging.py
"""Text processing operation logging implementation - SRP compliance.
"""
from datetime import datetime
from typing import Optional

import structlog


class StructuredTextProcessingLogger:
    """Structured logging implementation for text processing operations.
    Follows SRP - only responsible for logging.
    """

    def __init__(self, logger_name: str = "text_processing"):
        self._logger = structlog.get_logger(logger_name)

    async def log_operation(
        self,
        operation: str,
        media_id: str,
        format_type: str,
        success: bool,
        duration: float,
        text_length: Optional[int] = None,
        error: Optional[Exception] = None
    ) -> None:
        """Log text processing operation with structured data."""
        log_data = {
            "operation": operation,
            "media_id": media_id,
            "format_type": format_type,
            "success": success,
            "duration_seconds": duration,
            "timestamp": datetime.utcnow().isoformat()
        }

        if text_length is not None:
            log_data["text_length"] = text_length

        if error:
            log_data.update({
                "error_type": type(error).__name__,
                "error_message": str(error)
            })

        if success:
            self._logger.info(
                f"Text processing operation {operation} completed successfully",
                **log_data
            )
        else:
            self._logger.error(
                f"Text processing operation {operation} failed",
                **log_data
            )


class NoOpTextProcessingLogger:
    """No-operation logger for testing or when logging is disabled.
    Follows Null Object pattern.
    """

    async def log_operation(
        self,
        operation: str,
        media_id: str,
        format_type: str,
        success: bool,
        duration: float,
        text_length: Optional[int] = None,
        error: Optional[Exception] = None
    ) -> None:
        """No-op implementation."""
        pass
