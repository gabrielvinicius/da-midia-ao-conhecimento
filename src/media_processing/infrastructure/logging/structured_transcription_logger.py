# src/transcription/infrastructure/logging.py
from datetime import datetime, timezone
from typing import Optional

import structlog

from src.shared.infrastructure.observability.ports import LoggerPort


class StructuredTranscriptionLogger(LoggerPort):
    """Structured logging implementation for transcription operations.
    Follows SRP - only responsible for logging.
    """

    def __init__(self, logger_name: str = "transcription"):
        self._logger = structlog.get_logger(logger_name)

    async def log_operation(
        self,
        operation: str,
        media_id: str,
        provider: str,
        success: bool,
        duration: float,
        error: Optional[Exception] = None,
        **extra,
    ) -> None:
        """Log transcription operation with structured data."""
        log_data = {
            "operation": operation,
            "media_id": media_id,
            "provider": provider,
            "success": success,
            "duration_seconds": duration,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if error:
            log_data.update({
                "error_type": type(error).__name__,
                "error_message": str(error)
            })

        if success:
            self._logger.info(
                "Transcription operation completed successfully",
                **log_data
            )
        else:
            self._logger.error(
                "Transcription operation failed",
                **log_data
            )

    # Synchronous helpers for compatibility
    def info(self, message: str, **kwargs) -> None:
        self._logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        self._logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        self._logger.error(message, **kwargs)


class NoOpTranscriptionLogger(LoggerPort):
    """No-operation logger for testing or when logging is disabled.
    Follows Null Object pattern.
    """

    async def log_operation(
        self,
        operation: str,
        media_id: str,
        provider: str,
        success: bool,
        duration: float,
        error: Optional[Exception] = None,
        **extra,
    ) -> None:
        """No-op implementation."""
        pass

    def info(self, message: str, **kwargs) -> None:
        return None

    def warning(self, message: str, **kwargs) -> None:
        return None

    def error(self, message: str, **kwargs) -> None:
        return None
