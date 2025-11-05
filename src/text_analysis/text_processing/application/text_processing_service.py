# src/text_processing/application/text_processing_service.py
"""Consolidated Text Processing Service.
"""
from typing import Any, Dict, Optional
from uuid import UUID

import structlog

from src.text_analysis.text_processing.infrastructure.task_scheduler import (
    CeleryTextProcessingTaskScheduler,
)
from src.text_analysis.text_processing.infrastructure.text_extractor import (
    TextExtractor,
)
from src.text_analysis.text_processing.infrastructure.text_processor import (
    TextProcessor,
)

# TODO: Adicionar logger e metrics específicos para text_processing

logger = structlog.get_logger(__name__)


class TextProcessingService:
    """Consolidated service for all text processing operations.
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

    async def request_text_processing(self, media_id: UUID, text_content: str, processing_type: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Requests text processing by scheduling a task."""
        logger.info("text_processing.request_process.started", media_id=str(media_id), processing_type=processing_type)
        try:
            task_result = await self.task_scheduler.schedule_process_text_task(
                media_id=str(media_id),
                text_content=text_content,
                processing_type=processing_type,
                options=options
            )

            logger.info("text_processing.request_process.completed", media_id=str(media_id), task_id=task_result.get("task_id"))
            return {
                "success": True,
                "media_id": str(media_id),
                "task_id": task_result.get("task_id"),
                "message": "Text processing task scheduled successfully"
            }
        except Exception as e:
            logger.error("text_processing.request_process.failed", media_id=str(media_id), error=str(e))
            raise

    async def request_text_extraction(
        self,
        media_id: UUID,
        file_path: str,
        extraction_method: str,
        *,
        storage_provider: str = "local",
    ) -> Dict[str, Any]:
        """Requests text extraction by scheduling a task."""
        logger.info("text_processing.request_extract.started", media_id=str(media_id), file_path=file_path, extraction_method=extraction_method)
        try:
            task_result = await self.task_scheduler.schedule_extract_text_task(
                media_id=str(media_id),
                file_path=file_path,
                extraction_method=extraction_method,
                storage_provider=storage_provider,
            )

            logger.info("text_processing.request_extract.completed", media_id=str(media_id), task_id=task_result.get("task_id"))
            return {
                "success": True,
                "media_id": str(media_id),
                "task_id": task_result.get("task_id"),
                "message": "Text extraction task scheduled successfully"
            }
        except Exception as e:
            logger.error("text_processing.request_extract.failed", media_id=str(media_id), error=str(e))
            raise
