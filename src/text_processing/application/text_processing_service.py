# src/text_processing/application/text_processing_service.py
"""
Consolidated Text Processing Service.
"""
import structlog
from typing import Dict, Any, Optional
from uuid import UUID
import time

from src.text_processing.infrastructure.text_processor import TextProcessor
from src.text_processing.infrastructure.text_extractor import TextExtractor
from src.text_processing.infrastructure.task_scheduler import CeleryTextProcessingTaskScheduler
# TODO: Adicionar logger e metrics específicos para text_processing

logger = structlog.get_logger(__name__)


class TextProcessingService:
    """
    Consolidated service for all text processing operations.
    """
    
    def __init__(
        self,
        text_processor: TextProcessor,
        text_extractor: TextExtractor,
        task_scheduler: CeleryTextProcessingTaskScheduler,
        # TODO: Adicionar text_processing_logger, text_processing_metrics
    ):
        self.processor = text_processor
        self.extractor = text_extractor
        self.task_scheduler = task_scheduler
        # self.logger = text_processing_logger # Placeholder
        # self.metrics = text_processing_metrics # Placeholder

    async def process_text(self, media_id: UUID, text_content: str, processing_type: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Processes text content using the configured text processor."""
        start_time = time.monotonic()
        success = False
        error = None

        logger.info("text_processing.process.started", media_id=str(media_id), processing_type=processing_type)
        try:
            result = await self.processor.process_text(
                text_content=text_content,
                processing_type=processing_type,
                options=options
            )
            success = True
            logger.info("text_processing.process.completed", media_id=str(media_id))
            return {
                "success": True,
                "media_id": str(media_id),
                "processing_type": processing_type,
                "message": "Text processing completed successfully",
                "result": result
            }
        except Exception as e:
            error = e
            logger.error("text_processing.process.failed", media_id=str(media_id), error=str(e))
            raise
        finally:
            duration = time.monotonic() - start_time
            # TODO: Adicionar logging e métricas aqui
            # await self.logger.log_operation(...) # Placeholder
            # await self.metrics.record_operation(...) # Placeholder

    async def extract_text(self, media_id: UUID, file_path: str, extraction_method: str) -> Dict[str, Any]:
        """Extracts text from a file using the configured text extractor."""
        start_time = time.monotonic()
        success = False
        error = None

        logger.info("text_processing.extract.started", media_id=str(media_id), file_path=file_path, extraction_method=extraction_method)
        try:
            extracted_text = await self.extractor.extract_text(
                file_path=file_path,
                extraction_method=extraction_method
            )
            success = True
            logger.info("text_processing.extract.completed", media_id=str(media_id))
            return {
                "success": True,
                "media_id": str(media_id),
                "extraction_method": extraction_method,
                "message": "Text extraction completed successfully",
                "extracted_text": extracted_text
            }
        except Exception as e:
            error = e
            logger.error("text_processing.extract.failed", media_id=str(media_id), error=str(e))
            raise
        finally:
            duration = time.monotonic() - start_time
            # TODO: Adicionar logging e métricas aqui
            # await self.logger.log_operation(...) # Placeholder
            # await self.metrics.record_operation(...) # Placeholder

    async def request_text_processing(self, media_id: UUID, text_content: str, processing_type: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Requests text processing by scheduling a task."""
        logger.info("text_processing.request_process.started", media_id=str(media_id), processing_type=processing_type)
        try:
            # In a real scenario, this would schedule an async task.
            # For now, we'll call the processing directly.
            processing_result = await self.process_text(media_id, text_content, processing_type, options)
            
            logger.info("text_processing.request_process.completed", media_id=str(media_id))
            return {
                "success": True,
                "media_id": str(media_id),
                "message": "Text processing completed directly (or scheduled)"
            }
        except Exception as e:
            logger.error("text_processing.request_process.failed", media_id=str(media_id), error=str(e))
            raise

    async def request_text_extraction(self, media_id: UUID, file_path: str, extraction_method: str) -> Dict[str, Any]:
        """Requests text extraction by scheduling a task."""
        logger.info("text_processing.request_extract.started", media_id=str(media_id), file_path=file_path, extraction_method=extraction_method)
        try:
            # In a real scenario, this would schedule an async task.
            # For now, we'll call the extraction directly.
            extraction_result = await self.extract_text(media_id, file_path, extraction_method)
            
            logger.info("text_processing.request_extract.completed", media_id=str(media_id))
            return {
                "success": True,
                "media_id": str(media_id),
                "message": "Text extraction completed directly (or scheduled)"
            }
        except Exception as e:
            logger.error("text_processing.request_extract.failed", media_id=str(media_id), error=str(e))
            raise
