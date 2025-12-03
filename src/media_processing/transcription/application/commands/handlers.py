"""Compatibility handler that proxies to the refactored transcription services.

The refactor consolidated transcription orchestration inside
``TranscriptionService``.  Some integration tests – and potentially external
automation – still instantiates the old ``ProcessTranscriptionCommandHandler``.
This module reintroduces a thin wrapper with the same constructor signature,
delegating the work to the modern services so the refactor remains backwards
compatible.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from src.shared.domain.enums import MediaStatus
from src.media_processing.transcription.application.commands.commands import (
    ProcessTranscriptionCommand,
)
from src.media_processing.transcription.domain.transcription import (
    Transcription,
    TranscriptionStatus,
)


class ProcessTranscriptionCommandHandler:
    """Legacy handler facade that orchestrates the transcription pipeline."""

    def __init__(
        self,
        *,
        speech_recognition: Any,
        storage_service: Any,
        event_bus: Any,
        transcription_repository: Any,
        media_queries: Any,
        media_repository: Any,
        metrics_service: Optional[Any] = None,
    ) -> None:
        self._speech_recognition = speech_recognition
        self._storage_service = storage_service
        self._event_bus = event_bus
        self._transcription_repository = transcription_repository
        self._media_queries = media_queries
        self._media_repository = media_repository
        self._metrics_service = metrics_service

    async def handle(self, command: ProcessTranscriptionCommand) -> Dict[str, Any]:
        media_uuid = UUID(command.media_id)

        transcription = await self._transcription_repository.get_by_media_id(media_uuid)
        if transcription is None:
            transcription = Transcription(
                media_id=media_uuid,
                provider=command.transcription_provider,
            )
            transcription.process()
            await self._transcription_repository.add(transcription)
        else:
            transcription.provider = command.transcription_provider
            transcription.process()
            await self._transcription_repository.update(transcription)

        try:
            download_result = await self._storage_service.download(command.file_path)
            if isinstance(download_result, (list, tuple)):
                audio_bytes = download_result[0]
            else:
                audio_bytes = download_result

            recognition_payload = await self._speech_recognition.transcribe(
                audio_bytes,
                language=command.language,
            )

            result_payload = self._normalize_transcription_output(recognition_payload)
            transcription.mark_as_completed(result_payload)
            await self._transcription_repository.update(transcription)

            await self._media_repository.update_status(
                media_uuid,
                MediaStatus.COMPLETED,
            )

            if self._metrics_service is not None:
                await self._metrics_service.record_operation(
                    operation="process_transcription",
                    provider=command.transcription_provider,
                    success=True,
                    media_id=str(media_uuid),
                )

            return {
                "media_id": str(media_uuid),
                "transcription_id": str(transcription.id),
                "status": TranscriptionStatus.COMPLETED.value,
            }
        except Exception as exc:
            transcription.mark_as_failed(str(exc))
            await self._transcription_repository.update(transcription)
            await self._media_repository.update_status(
                media_uuid,
                MediaStatus.FAILED,
                error_message=str(exc),
            )

            if self._metrics_service is not None:
                await self._metrics_service.record_operation(
                    operation="process_transcription",
                    provider=command.transcription_provider,
                    success=False,
                    media_id=str(media_uuid),
                    error=str(exc),
                )

            raise

    @staticmethod
    def _normalize_transcription_output(payload: Any) -> Dict[str, Any]:
        if isinstance(payload, dict):
            return payload
        return {
            "text": str(payload),
            "segments": [],
        }


__all__ = ["ProcessTranscriptionCommandHandler"]
