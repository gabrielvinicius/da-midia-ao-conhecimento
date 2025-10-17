# src/topic_modeling/infrastructure/logging.py
"""
Topic modeling operation logging implementation - SRP compliance.
"""
import structlog
from typing import Optional
from datetime import datetime

from src.topic_modeling.domain.interfaces import TopicModelingOperationLogger


class StructuredTopicModelingLogger(TopicModelingOperationLogger):
    """
    Structured logging implementation for topic modeling operations.
    Follows SRP - only responsible for logging.
    """
    
    def __init__(self, logger_name: str = "topic_modeling"):
        self._logger = structlog.get_logger(logger_name)
    
    async def log_operation(
        self, 
        operation: str, 
        media_id: str,
        provider: str,
        language: str,
        success: bool,
        duration: float,
        num_topics: int = 0,
        text_length: int = 0,
        error: Optional[Exception] = None
    ) -> None:
        """Log topic modeling operation with structured data."""
        log_data = {
            "operation": operation,
            "media_id": media_id,
            "provider": provider,
            "language": language,
            "success": success,
            "duration_seconds": duration,
            "num_topics": num_topics,
            "text_length": text_length,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Calculate topics per second if relevant
        if success and duration > 0 and num_topics > 0:
            log_data["topics_per_second"] = num_topics / duration
        
        # Calculate processing rate
        if success and duration > 0 and text_length > 0:
            log_data["chars_per_second"] = text_length / duration
        
        if error:
            log_data.update({
                "error_type": type(error).__name__,
                "error_message": str(error)
            })
        
        if success:
            self._logger.info(
                f"Topic modeling operation {operation} completed successfully",
                **log_data
            )
        else:
            self._logger.error(
                f"Topic modeling operation {operation} failed",
                **log_data
            )


class NoOpTopicModelingLogger(TopicModelingOperationLogger):
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
        num_topics: int = 0,
        text_length: int = 0,
        error: Optional[Exception] = None
    ) -> None:
        """No-op implementation."""
        pass