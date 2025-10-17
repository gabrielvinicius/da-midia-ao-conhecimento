"""
Consolidated Summary Service - Replaces multiple services
"""
import structlog
from typing import Dict, Any, Optional
from uuid import UUID

from src.summarization.application.commands.commands import (
    ProcessSummaryCommand,
    RequestSummaryCommand
)
from src.summarization.application.commands.handlers import (
    ProcessSummaryCommandHandler,
    RequestSummaryCommandHandler
)

logger = structlog.get_logger(__name__)


class SummaryService:
    """Consolidated service for all summary operations."""
    
    def __init__(
        self,
        process_summary_handler: ProcessSummaryCommandHandler,
        request_summary_handler: RequestSummaryCommandHandler
    ):
        self.process_summary_handler = process_summary_handler
        self.request_summary_handler = request_summary_handler

    async def process_summary(self, media_id: str, text_content: str, provider: str) -> Dict[str, Any]:
        """Process summary with validation."""
        if not text_content or len(text_content) < 100:
            raise ValueError("Text too short for summarization")
        
        command = ProcessSummaryCommand(media_id=media_id, text_content=text_content, provider=provider)
        return await self.process_summary_handler.handle(command)
    
    async def request_summary(self, transcription_id: str, provider: str) -> Dict[str, Any]:
        """Request summary generation."""
        command = RequestSummaryCommand(transcription_id=transcription_id, provider=provider)
        return await self.request_summary_handler.handle(command)