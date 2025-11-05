"""Compatibility handler implementing the legacy video upload workflow."""

from __future__ import annotations

from typing import Any, Callable
from uuid import uuid4

from src.shared.events.domain_events import VideoUploaded
from src.video_management.application.commands.upload_video_command import (
    UploadVideoCommand,
)
from src.video_management.domain.video import Video


class UploadVideoCommandHandler:
    """Legacy handler that stores videos and publishes domain events."""

    def __init__(
        self,
        *,
        storage_service_factory: Callable[[str], Any],
        event_bus: Any,
        video_repository: Any,
        metrics_service: Any | None = None,
    ) -> None:
        self._storage_service_factory = storage_service_factory
        self._event_bus = event_bus
        self._video_repository = video_repository
        self._metrics_service = metrics_service

    async def handle(self, command: UploadVideoCommand) -> Video:
        storage_service = self._storage_service_factory(command.storage_provider)
        upload_result = await storage_service.upload(command.file, command.filename)

        storage_path = upload_result if isinstance(upload_result, str) else command.filename
        video = Video(
            id=uuid4(),
            user_id=command.user_id,
            storage_provider=command.storage_provider,
            file_path=storage_path,
            filename=command.filename,
        )

        await self._video_repository.save(video)

        await self._event_bus.publish(
            VideoUploaded(
                video_id=str(video.id),
                user_id=command.user_id,
                storage_provider=command.storage_provider,
                filename=command.filename,
            )
        )

        if self._metrics_service is not None:
            await self._metrics_service.observe_upload_duration(video_id=str(video.id))

        return video


__all__ = ["UploadVideoCommandHandler"]
