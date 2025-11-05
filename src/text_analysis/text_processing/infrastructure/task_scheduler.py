"""Celery scheduler facades for text processing tasks."""
from typing import Any, Dict, Optional

import structlog

logger = structlog.get_logger(__name__)


class CeleryTextProcessingTaskScheduler:
    """Thin wrapper that enfileira tarefas Celery relacionadas à extração/processamento de texto."""

    async def schedule_process_text_task(
        self,
        *,
        media_id: str,
        text_content: str,
        processing_type: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        logger.info(
            "text_processing.scheduler.process_text",
            media_id=media_id,
            processing_type=processing_type,
        )
        from src.text_analysis.tasks import process_text_task

        task = process_text_task.delay(
            media_id=media_id,
            text_content=text_content,
            processing_type=processing_type,
            options=options,
        )
        return {"task_id": getattr(task, "id", None)}

    async def schedule_extract_text_task(
        self,
        *,
        media_id: str,
        file_path: str,
        extraction_method: str,
        storage_provider: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.info(
            "text_processing.scheduler.extract_text",
            media_id=media_id,
            file_path=file_path,
            extraction_method=extraction_method,
            storage_provider=storage_provider,
        )
        from src.text_analysis.tasks import extract_text_task

        task = extract_text_task.delay(
            media_id=media_id,
            file_path=file_path,
            extraction_method=extraction_method,
            storage_provider=storage_provider,
        )
        return {"task_id": getattr(task, "id", None)}


__all__ = ["CeleryTextProcessingTaskScheduler"]
