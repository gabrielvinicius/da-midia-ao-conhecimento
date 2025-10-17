# src/summarization/domain/services/summary_coordinator.py
"""
Domain service for coordinating summarization operations - SRP compliance.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from src.summarization.domain.summary import Summary
from src.summarization.domain.interfaces import (
    SummaryProvider, 
    SummaryOperationLogger, 
    SummaryMetrics,
    SummaryNotificationService
)


class SummaryOperationError(Exception):
    """Domain exception for summarization operation errors."""
    pass


class SummaryCoordinator:
    """
    Domain service that coordinates summarization operations with logging and metrics.
    Follows SRP by focusing only on coordination logic.
    """
    
    def __init__(
        self,
        provider: SummaryProvider,
        logger: SummaryOperationLogger,
        metrics: SummaryMetrics,
        notification_service: SummaryNotificationService
    ):
        self._provider = provider
        self._logger = logger
        self._metrics = metrics
        self._notification_service = notification_service
    
    async def summarize_text(
        self, 
        media_id: str, 
        text_content: str,
        user_id: str
    ) -> str:
        """Summarize text with logging and metrics."""
        start_time = datetime.utcnow()
        success = False
        error = None
        input_length = len(text_content)
        output_length = 0
        
        try:
            # Validate input
            if not text_content or not text_content.strip():
                raise SummaryOperationError("Text content is empty or invalid")
            
            # Perform summarization
            summary_text = await self._provider.summarize(text_content)
            output_length = len(summary_text)
            success = True
            return summary_text
            
        except Exception as e:
            error = e
            success = False
            raise SummaryOperationError(f"Failed to summarize text for media {media_id}: {e}") from e
            
        finally:
            duration = (datetime.utcnow() - start_time).total_seconds()
            
            # Log operation
            await self._logger.log_operation(
                operation="summarize",
                media_id=media_id,
                provider=self._provider.provider_name,
                success=success,
                duration=duration,
                error=error
            )
            
            # Record metrics
            await self._metrics.record_operation(
                operation="summarize",
                provider=self._provider.provider_name,
                duration=duration,
                success=success,
                input_length=input_length,
                output_length=output_length
            )
    
    async def notify_status_change(
        self, 
        summary: Summary, 
        user_id: str, 
        status: str,
        error: Optional[str] = None
    ) -> None:
        """Notify status changes with error handling."""
        try:
            if status == "started":
                await self._notification_service.notify_started(summary, user_id)
            elif status == "completed":
                await self._notification_service.notify_completed(summary, user_id)
            elif status == "failed":
                await self._notification_service.notify_failed(summary, user_id, error or "Unknown error")
        except Exception as e:
            # Log notification failure but don't propagate
            await self._logger.log_operation(
                operation="notify",
                media_id=str(summary.media_id),
                provider=self._provider.provider_name,
                success=False,
                duration=0.0,
                error=e
            )