"""CQRS command for requesting transcription."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import UUID


@dataclass(slots=True)
class RequestTranscriptionCommand:
    media_id: UUID
    file_path: str
    storage_provider: str
    transcription_provider: str
    language: str
    metrics_payload: Optional[Dict[str, Any]] = None
    summarization_provider: Optional[str] = None
    sentiment_provider: Optional[str] = None
    topic_modeling_provider: Optional[str] = None
    file_size_bytes: Optional[int] = None


class RequestTranscriptionHandler:
    def __init__(self, service) -> None:
        self.service = service

    async def __call__(self, command: RequestTranscriptionCommand):
        return await self.service.request_transcription(
            media_id=command.media_id,
            file_path=command.file_path,
            storage_provider=command.storage_provider,
            transcription_provider=command.transcription_provider,
            language=command.language,
            metrics_payload=command.metrics_payload,
        )

