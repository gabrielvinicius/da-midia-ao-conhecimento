# src/storage/infrastructure/logging.py
"""Storage operation logging implementation - SRP compliance.
"""
from typing import Optional

import structlog

from src.shared.utils.time_utils import utcnow
from src.storage.domain.interfaces import StorageOperationLogger
from src.storage.domain.value_objects.file_path import FilePath


class StructuredStorageLogger(StorageOperationLogger):
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
        error: Optional[Exception] = None
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
                f"Storage operation {operation} completed successfully",
                **log_data
            )
        else:
            self._logger.error(
                f"Storage operation {operation} failed",
                **log_data
            )


class NoOpStorageLogger(StorageOperationLogger):
    """No-operation logger for testing or when logging is disabled.
    Follows Null Object pattern.
    """

    async def log_operation(
        self,
        operation: str,
        file_path: FilePath,
        success: bool,
        duration: float,
        error: Optional[Exception] = None
    ) -> None:
        """No-op implementation."""
        pass
