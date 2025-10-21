# src/summarization/application/commands/handlers.py
import structlog
from typing import Dict, Any
from uuid import UUID

from src.summarization.domain.interfaces import ISummarizer, ISummarizationRepository, ISummarizationTaskScheduler
from src.summarization.domain.summary import Summary # Para referenciar a entidade Summary
from src.summarization.application.commands.commands import ProcessSummaryCommand, RequestSummaryCommand

logger = structlog.get_logger(__name__)


class ProcessSummaryCommandHandler:
    """Handler for processing a summary after it has been generated."""

    def __init__(self, summarization_repo: ISummarizationRepository):
        self.summarization_repo = summarization_repo

    async def handle(self, command: ProcessSummaryCommand) -> Dict[str, Any]:
        logger.info(
            "summarization.process_summary.started",
            media_id=command.media_id,
            provider=command.provider
        )
        try:
            # 1. Get the summary entity
            summary = await self.summarization_repo.get_by_media_id(UUID(command.media_id))
            if not summary:
                logger.error("summarization.process_summary.failed", media_id=command.media_id, error="Summary not found for media_id")
                raise ValueError(f"Summary not found for media_id: {command.media_id}")

            # 2. Mark as completed with the generated text
            summary.mark_as_completed(command.text_content)
            await self.summarization_repo.update(summary)

            logger.info(
                "summarization.process_summary.completed",
                media_id=command.media_id,
                summary_id=str(summary.id)
            )
            return {
                "success": True,
                "media_id": command.media_id,
                "summary_id": str(summary.id),
                "status": summary.status.value,
                "message": "Summary processed successfully"
            }
        except Exception as e:
            logger.error(
                "summarization.process_summary.failed",
                media_id=command.media_id,
                error=str(e)
            )
            # Optionally, mark summary as failed in the repository
            summary = await self.summarization_repo.get_by_media_id(UUID(command.media_id))
            if summary:
                summary.mark_as_failed(str(e))
                await self.summarization_repo.update(summary)
            raise


class RequestSummaryCommandHandler:
    """Handler for requesting a new summary generation."""

    def __init__(self, summarization_repo: ISummarizationRepository, summarization_task_scheduler: ISummarizationTaskScheduler):
        self.summarization_repo = summarization_repo
        self.summarization_task_scheduler = summarization_task_scheduler

    async def handle(self, command: RequestSummaryCommand) -> Dict[str, Any]:
        logger.info(
            "summarization.request_summary.started",
            transcription_id=command.transcription_id,
            provider=command.provider
        )
        try:
            # 1. Fetch transcription content (this would typically come from another module/query)
            # For now, we'll use a placeholder.
            # In a real scenario, we'd query the transcription module for the text content
            # associated with transcription_id.
            transcription_text_content = "Placeholder transcription text content for summarization."
            media_id = UUID("a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11") # Placeholder media_id

            # 2. Create a new summary entity
            new_summary = Summary.create(media_id=media_id, provider=command.provider)
            await self.summarization_repo.add(new_summary)

            # 3. Schedule the summarization task
            task_result = await self.summarization_task_scheduler.schedule_summarization_task(
                media_id=str(media_id),
                text_content=transcription_text_content,
                provider=command.provider
            )

            logger.info(
                "summarization.request_summary.scheduled",
                transcription_id=command.transcription_id,
                summary_id=str(new_summary.id),
                task_id=task_result.get("task_id")
            )
            return {
                "success": True,
                "transcription_id": command.transcription_id,
                "summary_id": str(new_summary.id),
                "task_id": task_result.get("task_id"),
                "message": "Summarization task scheduled successfully"
            }
        except Exception as e:
            logger.error(
                "summarization.request_summary.failed",
                transcription_id=command.transcription_id,
                error=str(e)
            )
            raise
