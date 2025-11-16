# src/shared/application/task_orchestrator.py
"""Shared helpers for scheduling background tasks across bounded contexts."""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol

from src.notifications.application.schemas import NotificationTaskPayload
from src.notifications.tasks.notification_tasks import send_notification_task
# Removido import circular: from src.text_analysis.application.services import TextAnalysisService
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.text_analysis.application.services import TextAnalysisService


class VideoProcessingTaskScheduler(Protocol):
    """Protocol describing the scheduler required for video processing tasks."""

    async def schedule_process_video_task(self, media_id: str, file_path: str) -> Any:
        """Schedule the asynchronous processing of a video file."""


async def schedule_video_processing(
    task_scheduler: VideoProcessingTaskScheduler,
    *,
    media_id: str,
    file_path: str,
) -> Any:
    """Delegate video processing to the provided scheduler implementation."""
    if task_scheduler is None:
        raise ValueError("task_scheduler must be provided to schedule video processing tasks.")

    return await task_scheduler.schedule_process_video_task(
        media_id=media_id,
        file_path=file_path,
    )


async def schedule_sentiment_analysis(
    *,
    text_analysis_service: TextAnalysisService,
    transcription_id: str,
    text: str,
    provider: str,
    model: Optional[str] = None,
    media_id: Optional[str] = None,
    language: Optional[str] = None,
) -> Dict[str, Any]:
    """Trigger the sentiment analysis pipeline via the validated TextAnalysisService."""
    if text_analysis_service is None:
        raise ValueError("text_analysis_service is required to schedule sentiment analysis")

    return await text_analysis_service.schedule_sentiment_analysis_task(
        transcription_id=transcription_id,
        text=text,
        provider=provider,
        model=model,
        media_id=media_id,
        language=language,
    )


async def schedule_topic_modeling(
    *,
    text_analysis_service: TextAnalysisService,
    media_id: str,
    text_content: str,
    provider: str,
    language: str,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Trigger topic modeling through the validated TextAnalysisService."""
    if text_analysis_service is None:
        raise ValueError("text_analysis_service is required to schedule topic modeling")

    return await text_analysis_service.schedule_topic_modeling_task(
        media_id=media_id,
        text_content=text_content,
        provider=provider,
        language=language,
        options=options,
    )


def schedule_notification(
    *,
    user_id: str,
    message: str,
    notification_type: str,
    contact_info: Dict[str, Any],
) -> Any:
    """Trigger the notification Celery task."""
    payload = NotificationTaskPayload(
        user_id=user_id,
        message=message,
        notification_type=notification_type,
        contact_info=contact_info,
    )
    return send_notification_task.delay(**payload.model_dump())

