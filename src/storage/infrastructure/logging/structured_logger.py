# src/storage/infrastructure/logging.py
"""Storage operation logging implementation - SRP compliance.
"""
from typing import Optional

import structlog

from src.shared.application.observability import LoggerPort
from src.shared.domain.time.clock import utcnow
from src.storage.application.ports import StorageOperationLoggerPort
from src.storage.domain.value_objects.file_path import FilePath


class StructuredStorageLogger(StorageOperationLoggerPort, LoggerPort):
    """Structured logging implementation for storage operations.
    Follows SRP - only responsible for logging.
    """

    def __init__(self, logger_name: str = "storage"):
        self._logger = structlog.get_logger(logger_name)

    async def log_operation(
        self,
        operation: str,
        file_path: FilePath,
        success: bool,
        duration: float,
        error: Optional[Exception] = None,
        **extra,
    ) -> None:
        """Log storage operation with structured data."""
        log_data = {
            "operation": operation,
            "file_path": str(file_path),
            "success": success,
            "duration_seconds": duration,
            "timestamp": utcnow().isoformat()
        }

        if error:
            log_data.update({
                "error_type": type(error).__name__,
                "error_message": str(error)
            })

        if success:
            self._logger.info(
                "Storage operation completed successfully",
                **log_data,
            )
        else:
            self._logger.error(
                "Storage operation failed",
                **log_data,
            )

    def info(self, message: str, **kwargs) -> None:
        self._logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        self._logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs) -> None:
        self._logger.error(message, **kwargs)


class NoOpStorageLogger(StorageOperationLoggerPort, LoggerPort):
    """No-operation logger for testing or when logging is disabled.
    Follows Null Object pattern.
    """

    async def log_operation(
        self,
        operation: str,
        file_path: FilePath,
        success: bool,
        duration: float,
        error: Optional[Exception] = None,
        **extra,
    ) -> None:
        """No-op implementation."""
        return None

    def info(self, message: str, **kwargs) -> None:
        return None

    def warning(self, message: str, **kwargs) -> None:
        return None

    def error(self, message: str, **kwargs) -> None:
        return None
