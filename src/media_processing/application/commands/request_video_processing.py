"""CQRS command for requesting video processing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import UUID


@dataclass(slots=True)
class RequestVideoProcessingCommand:
    media_id: UUID
    file_path: str
    storage_provider: str
    metrics_payload: Optional[Dict[str, Any]] = None
    file_size_bytes: Optional[int] = None


class RequestVideoProcessingHandler:
    def __init__(self, service) -> None:
        self.service = service

    async def __call__(self, command: RequestVideoProcessingCommand):
        return await self.service.request_video_processing(
            media_id=command.media_id,
            file_path=command.file_path,
            storage_provider=command.storage_provider,
            metrics_payload=command.metrics_payload,
        )

