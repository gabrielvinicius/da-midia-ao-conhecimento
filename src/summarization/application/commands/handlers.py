"""
Summarization Command Handlers - Pure execution logic following Command Pattern
"""
import structlog
from typing import Dict, Any

from src.media_management.application.queries.media_queries import MediaQueries
from src.summarization.domain.interfaces import SummaryOrchestrator
from .commands import (
    ProcessSummaryCommand,
    RequestSummaryCommand
)

logger = structlog.get_logger(__name__)


class ProcessSummaryCommandHandler:
    """Handler for process summary command"""
    
    def __init__(
        self,
        orchestrator: SummaryOrchestrator,
        media_queries: MediaQueries
    ):
        self._orchestrator = orchestrator
        self._media_queries = media_queries
    
    async def handle(self, command: ProcessSummaryCommand) -> Dict[str, Any]:
        """Execute process summary command"""
        logger.info(
            "summarization.command.process_started",
            media_id=command.media_id,
            provider=command.provider
        )
        
        try:
            media = await self._media_queries.get_by_id(command.media_id)
            if not media:
                return {
                    "success": False,
                    "error": f"Media with id {command.media_id} not found",
                    "message": "Media not found"
                }
            
            user_id = str(media.user_id)
            
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
            
            return {
                "success": True,
                "summary": {
                    "id": str(summary.id),
                    "media_id": command.media_id,
                    "text": summary.summary_text,
                    "provider": command.provider
                },
                "message": "Summary processed successfully"
            }
            
        except Exception as e:
            logger.error(
                "summarization.command.process_failed",
                media_id=command.media_id,
                error=str(e)
            )
            return {
                "success": False,
                "error": str(e),
                "message": f"Summary processing failed: {str(e)}"
            }


class RequestSummaryCommandHandler:
    """Handler for request summary command"""
    
    def __init__(self, orchestrator: SummaryOrchestrator):
        self._orchestrator = orchestrator

    async def handle(self, command: RequestSummaryCommand) -> Dict[str, Any]:
        """Execute summary request command"""
        logger.info(
            "summarization.command.request_started",
            transcription_id=command.transcription_id,
            provider=command.provider
        )
        
        try:
            summary = await self._orchestrator.request_summary(
                transcription_id=command.transcription_id,
                provider=command.provider
            )
            
            logger.info(
                "summarization.command.request_completed",
                transcription_id=command.transcription_id,
                summary_id=str(summary.id) if summary else None
            )
            
            return {
                "success": True,
                "summary": {
                    "id": str(summary.id),
                    "transcription_id": command.transcription_id,
                    "provider": command.provider
                } if summary else None,
                "message": "Summary request processed successfully"
            }
            
        except Exception as e:
            logger.error(
                "summarization.command.request_failed",
                transcription_id=command.transcription_id,
                error=str(e)
            )
            return {
                "success": False,
                "error": str(e),
                "message": f"Summary request failed: {str(e)}"
            }