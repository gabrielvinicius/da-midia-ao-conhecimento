# src/summarization/application/summarization_service.py
"""
Consolidated Summarization Service.
"""
import structlog
from typing import Dict, Any, Optional
from uuid import UUID
import time

from src.summarization.domain.summary import Summary, SummaryStatus
from src.summarization.infrastructure.summarization_repository import SummarizationRepository
from src.summarization.infrastructure.task_scheduler import CelerySummarizationTaskScheduler
from src.summarization.infrastructure.logging import StructuredSummaryLogger
from src.summarization.infrastructure.metrics import PrometheusSummaryMetrics

logger = structlog.get_logger(__name__)

class SummarizationService:
    """Application service for orchestrating summarization operations."""

    def __init__(
        self,
        summarization_repo: SummarizationRepository,
        task_scheduler: CelerySummarizationTaskScheduler,
        summary_logger: StructuredSummaryLogger,
        summary_metrics: PrometheusSummaryMetrics
    ):
        self.repo = summarization_repo
        self.task_scheduler = task_scheduler
        self.logger = summary_logger
        self.metrics = summary_metrics

    async def request_summary(self, transcription_id: str, provider: str) -> Dict[str, Any]:
        """Requests and schedules a new summary generation."""
        start_time = time.monotonic()
        success = False
        error = None
        media_id_str = ""

        logger.info("summarization.request.started", transcription_id=transcription_id, provider=provider)
        try:
            # Placeholder logic to get transcription text and media_id
            transcription_text_content = f"This is the full text from transcription {transcription_id}."
            media_id = UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11") # Placeholder
            media_id_str = str(media_id)

            new_summary = Summary.create(media_id=media_id, provider=provider)
            await self.repo.add(new_summary)

            task_result = await self.task_scheduler.schedule_summarization_task(
                media_id=media_id_str,
                text_content=transcription_text_content,
                provider=provider
            )
            success = True
            logger.info("summarization.request.scheduled", summary_id=str(new_summary.id))
            return {
                "summary_id": str(new_summary.id),
                "task_id": task_result.get("task_id"),
            }
        except Exception as e:
            error = e
            logger.error("summarization.request.failed", transcription_id=transcription_id, error=str(e))
            raise
        finally:
            duration = time.monotonic() - start_time
            await self.logger.log_operation(
                operation="request_summary",
                media_id=media_id_str,
                provider=provider,
                success=success,
                duration=duration,
                error=error
            )
            # Metrics can be added here

    async def process_summary(self, media_id: str, provider: str, text_content: str) -> Summary:
        """Processes a generated summary and marks it as complete."""
        logger.info("summarization.process.started", media_id=media_id, provider=provider)
        summary = await self.repo.get_by_media_id(UUID(media_id))
        if not summary:
            raise ValueError(f"Summary not found for media_id: {media_id}")

        summary = summary.mark_as_completed(text_content)
        summary = await self.repo.update(summary)
        logger.info("summarization.process.completed", summary_id=str(summary.id))
        return summary

    async def get_summary_by_media_id(self, media_id: UUID) -> Optional[Summary]:
        return await self.repo.get_by_media_id(media_id)

    async def get_summary_by_id(self, summary_id: UUID) -> Optional[Summary]:
        return await self.repo.get_by_id(summary_id)
