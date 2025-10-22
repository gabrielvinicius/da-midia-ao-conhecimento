# src/media_management/infrastructure/logging.py
import structlog
from typing import Optional
from datetime import datetime
from uuid import UUID

from src.media_management.domain.interfaces import MediaOperationLogger


class StructuredMediaLogger(MediaOperationLogger):
    """
    Structured logging implementation for media management operations.
    Follows SRP - only responsible for logging.
    """
    
    def __init__(self, logger_name: str = "media_management"):
        self._logger = structlog.get_logger(logger_name)
    
    async def log_operation(
        self, 
        operation: str, 
        media_id: str,
        user_id: str,
        success: bool,
        duration: float,
        error: Optional[Exception] = None
    ) -> None:
        """Log media management operation with structured data."""
        log_data = {
            "operation": operation,
            "media_id": media_id,
            "user_id": user_id,
            "success": success,
            "duration_seconds": duration,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if error:
            log_data.update({
                "error_type": type(error).__name__,
                "error_message": str(error)
            })
        
        if success:
            self._logger.info(
                f"Media management operation {operation} completed successfully",
                **log_data
            )
        else:
            self._logger.error(
                f"Media management operation {operation} failed",
                **log_data
            )


class NoOpMediaLogger(MediaOperationLogger):
    """
    No-operation logger for testing or when logging is disabled.
    Follows Null Object pattern.
    """
    
    async def log_operation(
        self, 
        operation: str, 
        media_id: str,
        user_id: str,
        success: bool,
        duration: float,
        error: Optional[Exception] = None
    ) -> None:
        """No-op implementation."""
        pass
