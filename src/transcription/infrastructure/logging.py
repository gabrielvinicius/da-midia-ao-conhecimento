# src/transcription/infrastructure/logging.py
"""
Transcription operation logging implementation - SRP compliance.
"""
import structlog
from typing import Optional
from datetime import datetime

from src.transcription.domain.interfaces import TranscriptionOperationLogger


class StructuredTranscriptionLogger(TranscriptionOperationLogger):
    """
    Structured logging implementation for transcription operations.
    Follows SRP - only responsible for logging.
    """
    
    def __init__(self, logger_name: str = "transcription"):
        self._logger = structlog.get_logger(logger_name)
    
    async def log_operation(
        self, 
        operation: str, 
        media_id: str,
        provider: str,
        language: str,
        success: bool,
        duration: float,
        audio_duration: Optional[float] = None,
        error: Optional[Exception] = None
    ) -> None:
        """Log transcription operation with structured data."""
        log_data = {
            "operation": operation,
            "media_id": media_id,
            "provider": provider,
            "language": language,
            "success": success,
            "duration_seconds": duration,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if audio_duration is not None:
            log_data["audio_duration_seconds"] = audio_duration
            # Calculate real-time factor (RTF)
            if audio_duration > 0:
                log_data["rtf"] = duration / audio_duration
        
        if error:
            log_data.update({
                "error_type": type(error).__name__,
                "error_message": str(error)
            })
        
        if success:
            self._logger.info(
                f"Transcription operation {operation} completed successfully",
                **log_data
            )
        else:
            self._logger.error(
                f"Transcription operation {operation} failed",
                **log_data
            )


class NoOpTranscriptionLogger(TranscriptionOperationLogger):
    """
    No-operation logger for testing or when logging is disabled.
    Follows Null Object pattern.
    """
    
    async def log_operation(
        self, 
        operation: str, 
        media_id: str,
        provider: str,
        language: str,
        success: bool,
        duration: float,
        audio_duration: Optional[float] = None,
        error: Optional[Exception] = None
    ) -> None:
        """No-op implementation."""
        pass