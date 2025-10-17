# src/summarization/application/services/summary_state_manager.py
"""
Summary state management service - SRP compliance.
"""
from typing import Optional
import structlog

from src.summarization.domain.interfaces import SummaryStateManager, ISummaryRepository
from src.summarization.domain.summary import Summary

logger = structlog.get_logger(__name__)


class SummaryStateManagerImpl(SummaryStateManager):
    """
    Implementation of summary state management.
    Follows SRP - only responsible for state transitions.
    """
    
    def __init__(self, repository: ISummaryRepository):
        self._repository = repository
    
    async def start_processing(self, media_id: str, provider: str) -> Summary:
        """Start processing and return summary."""
        logger.info(
            "summary.state.start_processing",
            media_id=media_id,
            provider=provider
        )
        
        # Check if summary already exists
        existing_summary = await self._repository.find_by_media_id(media_id)
        
        if existing_summary:
            # Update existing summary
            existing_summary.provider = provider
            existing_summary.status = Summary.SummaryStatus.PROCESSING
            existing_summary.error_message = None
            summary = await self._repository.save(existing_summary)
            
            logger.info(
                "summary.state.restarted_existing",
                summary_id=str(summary.id),
                media_id=media_id
            )
        else:
            # Create new summary
            summary = Summary.create(media_id=media_id, provider=provider)
            summary = await self._repository.save(summary)
            
            logger.info(
                "summary.state.created_new",
                summary_id=str(summary.id),
                media_id=media_id
            )
        
        return summary
    
    async def complete_processing(self, summary: Summary, text: str) -> Summary:
        """Complete processing with result."""
        logger.info(
            "summary.state.complete_processing",
            summary_id=str(summary.id),
            text_length=len(text)
        )
        
        # Validate state transition
        if summary.status != Summary.SummaryStatus.PROCESSING:
            logger.warning(
                "summary.state.invalid_transition",
                summary_id=str(summary.id),
                current_status=summary.status.value,
                attempted_transition="complete"
            )
        
        # Update summary
        summary.mark_as_completed(text)
        updated_summary = await self._repository.save(summary)
        
        logger.info(
            "summary.state.completed",
            summary_id=str(updated_summary.id),
            text_length=len(text)
        )
        
        return updated_summary
    
    async def fail_processing(self, summary: Summary, error: str) -> Summary:
        """Mark processing as failed."""
        logger.info(
            "summary.state.fail_processing",
            summary_id=str(summary.id),
            error=error
        )
        
        # Truncate error message if too long
        truncated_error = error[:500] if len(error) > 500 else error
        
        # Update summary
        summary.mark_as_failed(truncated_error)
        updated_summary = await self._repository.save(summary)
        
        logger.error(
            "summary.state.failed",
            summary_id=str(updated_summary.id),
            error=truncated_error
        )
        
        return updated_summary
    
    async def get_summary_state(self, media_id: str) -> Optional[Summary]:
        """Get current summary state for media."""
        return await self._repository.find_by_media_id(media_id)
    
    async def is_processing(self, media_id: str) -> bool:
        """Check if summarization is currently processing."""
        summary = await self._repository.find_by_media_id(media_id)
        return summary is not None and summary.status == Summary.SummaryStatus.PROCESSING
    
    async def reset_failed_summary(self, media_id: str) -> Optional[Summary]:
        """Reset a failed summary to allow reprocessing."""
        summary = await self._repository.find_by_media_id(media_id)
        
        if summary and summary.status == Summary.SummaryStatus.FAILED:
            summary.status = Summary.SummaryStatus.PENDING
            summary.error_message = None
            updated_summary = await self._repository.save(summary)
            
            logger.info(
                "summary.state.reset",
                summary_id=str(updated_summary.id),
                media_id=media_id
            )
            
            return updated_summary
        
        return None