"""
Text Processing Command Handlers - Pure execution logic following Command Pattern
"""
import structlog
from typing import Dict, Any

from src.text_processing.domain.interfaces import ITextProcessor, ITextExtractor # Adicionar esta linha
from .commands import (
    ProcessTextCommand,
    ExtractTextCommand
)

logger = structlog.get_logger(__name__)


class ProcessTextCommandHandler:
    """Handler for process text command"""

    def __init__(self, text_processor: ITextProcessor): # Adicionar construtor
        self.text_processor = text_processor

    async def handle(self, command: ProcessTextCommand) -> Dict[str, Any]:
        """Execute text processing command"""
        logger.info(
            "text.process.started",
            media_id=command.media_id,
            processing_type=command.processing_type
        )
        
        try:
            # Chamar o serviço de processamento de texto
            result = await self.text_processor.process_text(
                text_content=command.text_content,
                processing_type=command.processing_type,
                options=command.options
            )
            logger.info(
                "text.process.completed",
                media_id=command.media_id
            )
            
            return {
                "success": True,
                "media_id": command.media_id,
                "processing_type": command.processing_type,
                "message": "Text processing completed successfully",
                "result": result # Incluir o resultado do processamento
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

    def __init__(self, text_extractor: ITextExtractor): # Adicionar construtor
        self.text_extractor = text_extractor
    
    async def handle(self, command: ExtractTextCommand) -> Dict[str, Any]:
        """Execute text extraction command"""
        logger.info(
            "text.extract.started",
            media_id=command.media_id,
            method=command.extraction_method
        )
        
        try:
            # Chamar o serviço de extração de texto
            extracted_text = await self.text_extractor.extract_text(
                file_path=command.file_path,
                extraction_method=command.extraction_method
            )
            logger.info(
                "text.extract.completed",
                media_id=command.media_id
            )
            
            return {
                "success": True,
                "media_id": command.media_id,
                "extraction_method": command.extraction_method,
                "message": "Text extraction completed successfully",
                "extracted_text": extracted_text # Incluir o texto extraído
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