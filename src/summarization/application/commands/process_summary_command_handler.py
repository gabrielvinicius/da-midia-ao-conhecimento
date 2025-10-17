# src/summarization/application/commands/process_summary_command_handler.py
"""
Process summary command handler following SOLID principles.
"""
import structlog

from src.media_management.application.queries.media_queries import MediaQueries
from src.summarization.application.commands.process_summary_command import ProcessSummaryCommand
from src.summarization.domain.interfaces import SummaryOrchestrator

logger = structlog.get_logger(__name__)


class ProcessSummaryCommandHandler:
    """
    Command handler for processing summaries following SOLID principles.
    SRP: Only handles command processing and delegation.
    DIP: Depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        orchestrator: SummaryOrchestrator,
        media_queries: MediaQueries
    ):
        self._orchestrator = orchestrator
        self._media_queries = media_queries
    
    async def handle(self, command: ProcessSummaryCommand):
        """Handle process summary command."""
        logger.info(
            "summarization.command.process_started",
            media_id=command.media_id,
            provider=command.provider
        )
        
        # Get media information
        media = await self._media_queries.get_by_id(command.media_id)
        if not media:
            raise ValueError(f"Media with id {command.media_id} not found.")
        
        user_id = str(media.user_id)
        
        try:
            # Delegate to orchestrator (follows DIP)
            summary = await self._orchestrator.process_summarization(
                media_id=command.media_id,
                text_content=command.text_content,
                provider=command.provider,
                user_id=user_id
            )
            
            logger.info(
                "summarization.command.process_completed",
                media_id=command.media_id,
                summary_id=str(summary.id)
            )
            
            return summary
            
        except Exception as e:
            logger.error(
                "summarization.command.process_failed",
                media_id=command.media_id,
                error=str(e)
            )
            raise