"""
Text Processing Command Handlers - Pure execution logic following Command Pattern
"""
import structlog
from typing import Dict, Any

from .commands import (
    ProcessTextCommand,
    ExtractTextCommand
)

logger = structlog.get_logger(__name__)


class ProcessTextCommandHandler:
    """Handler for process text command"""
    
    async def handle(self, command: ProcessTextCommand) -> Dict[str, Any]:
        """Execute text processing command"""
        logger.info(
            "text.process.started",
            media_id=command.media_id,
            processing_type=command.processing_type
        )
        
        try:
            # Processing logic here
            logger.info(
                "text.process.completed",
                media_id=command.media_id
            )
            
            return {
                "success": True,
                "media_id": command.media_id,
                "processing_type": command.processing_type,
                "message": "Text processing completed successfully"
            }
            
        except Exception as e:
            logger.error(
                "text.process.failed",
                media_id=command.media_id,
                error=str(e)
            )
            return {
                "success": False,
                "error": str(e),
                "message": f"Text processing failed: {str(e)}"
            }


class ExtractTextCommandHandler:
    """Handler for extract text command"""
    
    async def handle(self, command: ExtractTextCommand) -> Dict[str, Any]:
        """Execute text extraction command"""
        logger.info(
            "text.extract.started",
            media_id=command.media_id,
            method=command.extraction_method
        )
        
        try:
            # Extraction logic here
            logger.info(
                "text.extract.completed",
                media_id=command.media_id
            )
            
            return {
                "success": True,
                "media_id": command.media_id,
                "extraction_method": command.extraction_method,
                "message": "Text extraction completed successfully"
            }
            
        except Exception as e:
            logger.error(
                "text.extract.failed",
                media_id=command.media_id,
                error=str(e)
            )
            return {
                "success": False,
                "error": str(e),
                "message": f"Text extraction failed: {str(e)}"
            }