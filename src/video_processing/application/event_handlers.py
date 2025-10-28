# src/video_processing/application/event_handlers.py
import logging
from typing import Dict, Any

from src.shared.events.event_bus import EventBus
from src.media_management.domain.media import MediaType
from src.shared.events.domain_events import MediaUploaded
# FIXED: Application should not import Tasks directly (Infrastructure concern)
from src.shared.application.task_orchestrator import (
    VideoProcessingTaskScheduler,
    schedule_video_processing,
)

logger = logging.getLogger(__name__)


async def register_event_handlers(
    event_bus: EventBus,
    task_scheduler: VideoProcessingTaskScheduler,
) -> None:
    """Registers all video processing-related event handlers."""

    async def handle_media_uploaded(event_data: Dict[str, Any]) -> None:
        """Handles MediaUploaded events by triggering the video processing task if the media is a video."""
        try:
            media_type = event_data.get("media_type")
            if media_type == MediaType.VIDEO.value:
                media_id = event_data["media_id"]
                file_path = event_data["file_path"]
                logger.info(f"Video media uploaded. Dispatching video processing task for media {media_id}")
                await schedule_video_processing(
                    task_scheduler=task_scheduler,
                    media_id=media_id,
                    file_path=file_path,
                )

        except KeyError as e:
            logger.error(f"Missing required field in MediaUploaded event data: {e}")
        except Exception as e:
            logger.error(f"Failed to handle MediaUploaded event for video processing: {e}", exc_info=True)

    try:
        event_bus.subscribe(MediaUploaded, handle_media_uploaded)
        logger.info("Successfully registered MediaUploaded handler for video processing.")
    except Exception as e:
        logger.error(f"Failed to register video processing event handlers: {e}", exc_info=True)
        raise
