# src/summarization/application/services/summary_orchestrator.py
"""
Summary orchestrator implementation - DIP compliance.
"""
from typing import Optional
import structlog

from src.summarization.domain.interfaces import (
    SummaryOrchestrator,
    ISummaryRepository,
    SummaryStateManager
)
from src.summarization.domain.summary import Summary
from src.summarization.domain.services.summary_coordinator import SummaryCoordinator

logger = structlog.get_logger(__name__)


class SummaryOrchestratorImpl(SummaryOrchestrator):
    """
    High-level orchestrator for summarization operations.
    Follows DIP - depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        repository: ISummaryRepository,
        state_manager: SummaryStateManager,
        coordinator: SummaryCoordinator
    ):
        self._repository = repository
        self._state_manager = state_manager
        self._coordinator = coordinator
    
    async def process_summarization(
        self, 
        media_id: str, 
        text_content: str, 
        provider: str,
        user_id: str
    ) -> Summary:
        """Process complete summarization workflow."""
        logger.info(
            "summarization.orchestrator.start",
            media_id=media_id,
            provider=provider,
            user_id=user_id,
            text_length=len(text_content)
        )
        
        # Check if already processing
        if await self._state_manager.is_processing(media_id):
            existing_summary = await self._state_manager.get_summary_state(media_id)
            logger.warning(
                "summarization.orchestrator.already_processing",
                media_id=media_id,
                summary_id=str(existing_summary.id) if existing_summary else None
            )
            return existing_summary
        
        summary = None
        try:
            # 1. Start processing
            summary = await self._state_manager.start_processing(media_id, provider)
            await self._coordinator.notify_status_change(summary, user_id, "started")
            
            # 2. Perform summarization
            summary_text = await self._coordinator.summarize_text(
                media_id=media_id,
                text_content=text_content,
                user_id=user_id
            )
            
            # 3. Complete processing
            summary = await self._state_manager.complete_processing(summary, summary_text)
            await self._coordinator.notify_status_change(summary, user_id, "completed")
            
            logger.info(
                "summarization.orchestrator.completed",
                media_id=media_id,
                summary_id=str(summary.id),
                output_length=len(summary_text)
            )
            
            return summary
            
        except Exception as e:
            logger.error(
                "summarization.orchestrator.failed",
                media_id=media_id,
                error=str(e),
                summary_id=str(summary.id) if summary else None
            )
            
            # Handle failure
            if summary:
                summary = await self._state_manager.fail_processing(summary, str(e))
                await self._coordinator.notify_status_change(
                    summary, user_id, "failed", str(e)
                )
            
            raise
    
    async def get_summary(self, media_id: str) -> Optional[Summary]:
        """Get existing summary."""
        return await self._repository.find_by_media_id(media_id)
    
    async def retry_failed_summary(
        self,
        media_id: str,
        text_content: str,
        provider: str,
        user_id: str
    ) -> Summary:
        """Retry a failed summarization."""
        logger.info(
            "summarization.orchestrator.retry",
            media_id=media_id,
            provider=provider
        )
        
        # Reset failed summary
        await self._state_manager.reset_failed_summary(media_id)
        
        # Process again
        return await self.process_summarization(
            media_id=media_id,
            text_content=text_content,
            provider=provider,
            user_id=user_id
        )
    
    async def get_summary_status(self, media_id: str) -> Optional[str]:
        """Get current summary status."""
        summary = await self._repository.find_by_media_id(media_id)
        return summary.status.value if summary else None
    
    async def delete_summary(self, media_id: str) -> bool:
        """Delete summary for media."""
        logger.info("summarization.orchestrator.delete", media_id=media_id)
        return await self._repository.delete_by_media_id(media_id)