# src/shared/application/task_orchestrator.py
"""Shared helpers for scheduling background tasks across bounded contexts."""

from __future__ import annotations

from typing import Any, Dict, Optional, Protocol

from src.notifications.tasks.notification_tasks import send_notification_task
from src.text_analysis.sentiment_analysis.tasks.analysis_tasks import analyze_sentiment_task
from src.text_analysis.topic_modeling.tasks.topic_modeling_tasks import analyze_topics_task


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


def schedule_sentiment_analysis(
    *,
    media_id: str,
    text_content: str,
    provider: str,
) -> Any:
    """Trigger the sentiment analysis Celery task."""

    return analyze_sentiment_task.delay(
        media_id=media_id,
        text_content=text_content,
        provider=provider,
    )


def schedule_topic_modeling(
    *,
    media_id: str,
    text_content: str,
    provider: str,
    language: str,
    options: Optional[Dict[str, Any]] = None,
) -> Any:
    """Trigger the topic modeling Celery task."""

    return analyze_topics_task.delay(
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

    return send_notification_task.delay(
        user_id=user_id,
        message=message,
        notification_type=notification_type,
        contact_info=contact_info,
    )

