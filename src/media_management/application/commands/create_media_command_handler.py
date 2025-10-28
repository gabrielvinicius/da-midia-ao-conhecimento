# src/media_management/application/commands/create_media_command_handler.py
"""Command handler responsible for media creation workflows."""

from __future__ import annotations

import mimetypes
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import structlog

from src.media_management.domain.enums import MediaStatus, MediaType
from src.media_management.domain.media import Media
from src.shared.events.domain_events import MediaUploaded
from src.shared.exceptions.domain_exceptions import ValidationError

from .create_media_command import CreateMediaCommand

logger = structlog.get_logger(__name__)


class CreateMediaCommandHandler:
    """Coordinates media upload, persistence, metrics and event publication."""

    MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500MB
    MIN_FILE_SIZE_BYTES = 1 * 1024  # 1KB

    _MEDIA_TYPE_MAP: Dict[str, MediaType] = {
        ".mp3": MediaType.AUDIO,
        ".wav": MediaType.AUDIO,
        ".flac": MediaType.AUDIO,
        ".aac": MediaType.AUDIO,
        ".ogg": MediaType.AUDIO,
        ".m4a": MediaType.AUDIO,
        ".mp4": MediaType.VIDEO,
        ".avi": MediaType.VIDEO,
        ".mov": MediaType.VIDEO,
        ".mkv": MediaType.VIDEO,
        ".webm": MediaType.VIDEO,
        ".flv": MediaType.VIDEO,
        ".txt": MediaType.TEXT,
        ".pdf": MediaType.TEXT,
        ".doc": MediaType.TEXT,
        ".docx": MediaType.TEXT,
    }

    def __init__(
        self,
        media_repository: Any,
        storage_service_factory: Any,
        event_bus: Any,
        metrics_service: Any,
    ) -> None:
        self.media_repository = media_repository
        self.storage_service_factory = storage_service_factory
        self.event_bus = event_bus
        self.metrics_service = metrics_service

    async def handle(self, command: CreateMediaCommand) -> Media:
        """Execute the command returning the persisted media entity."""

        self._validate_file(command.file, command.filename)
        media_type = self._detect_media_type(command.filename)
        content_type = self._guess_mime_type(command.filename)

        storage_service = self._resolve_storage_service(command.storage_provider)
        media_id = uuid.uuid4()
        destination_path = self._build_destination_path(media_id, command.filename)

        upload_metadata = await storage_service.upload(
            destination_path=destination_path,
            content=command.file,
            filename=command.filename,
            content_type=content_type,
            metadata=command.metadata or {},
        )

        stored_path = self._extract_file_path(upload_metadata, destination_path)
        file_size = self._extract_file_size(upload_metadata, command.file)

        media = Media(
            id=media_id,
            user_id=command.user_id,
            original_file_path=stored_path,
            media_type=media_type,
            storage_provider=command.storage_provider,
            transcription_provider=command.transcription_provider,
            summarization_provider=command.summarization_provider,
            status=MediaStatus.UPLOADED,
        )

        # Attach additional metadata that is useful for consumers and tests.
        media.filename = command.filename
        media.file_size = file_size
        media.mime_type = content_type
        media.created_at = getattr(media, "created_at", datetime.now(timezone.utc))

        saved_media = await self._persist_media(media)

        await self._publish_metrics(saved_media, file_size)
        await self._publish_event(saved_media, stored_path)

        logger.info(
            "media_management.create_media.completed",
            media_id=str(saved_media.id),
            user_id=str(getattr(saved_media, "user_id", command.user_id)),
            media_type=saved_media.media_type.value if hasattr(saved_media.media_type, "value") else saved_media.media_type,
            storage_provider=saved_media.storage_provider,
        )

        return saved_media

    async def _persist_media(self, media: Media) -> Media:
        if hasattr(self.media_repository, "save"):
            saved_media = await self.media_repository.save(media)
        else:
            await self.media_repository.add(media)
            saved_media = media

        session = getattr(self.media_repository, "db", None)
        if session is not None and hasattr(session, "commit"):
            await session.commit()

        return saved_media

    async def _publish_metrics(self, media: Media, file_size: int) -> None:
        if hasattr(self.metrics_service, "increment_counter"):
            self.metrics_service.increment_counter(
                "media_uploads_total",
                media_type=media.media_type.value if isinstance(media.media_type, MediaType) else media.media_type,
                storage_provider=media.storage_provider,
            )

        if hasattr(self.metrics_service, "record_histogram"):
            self.metrics_service.record_histogram(
                "media_upload_file_size_bytes",
                file_size,
                media_type=media.media_type.value if isinstance(media.media_type, MediaType) else media.media_type,
            )

    async def _publish_event(self, media: Media, file_path: str) -> None:
        event = MediaUploaded(
            media_id=str(media.id),
            user_id=str(getattr(media, "user_id", "")),
            media_type=media.media_type,
            file_path=file_path,
            storage_provider=media.storage_provider,
            transcription_provider=getattr(media, "transcription_provider", None),
            summarization_provider=getattr(media, "summarization_provider", None),
        )
        await self.event_bus.publish(event)

    def _validate_file(self, file_data: bytes, filename: str) -> None:
        if not file_data:
            raise ValidationError("file", filename, "File content is empty")

        file_size = len(file_data)
        if file_size > self.MAX_FILE_SIZE_BYTES:
            raise ValidationError("file", filename, "File size exceeds maximum limit")

        if file_size < self.MIN_FILE_SIZE_BYTES:
            raise ValidationError("file", filename, "File size is too small")

    def _detect_media_type(self, filename: str) -> MediaType:
        _, ext = os.path.splitext(filename or "")
        media_type = self._MEDIA_TYPE_MAP.get(ext.lower())
        if not media_type:
            raise ValidationError("filename", filename, "Unsupported file type")
        return media_type

    def _guess_mime_type(self, filename: str) -> str:
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"

    def _resolve_storage_service(self, storage_provider: str) -> Any:
        factory = self.storage_service_factory
        if callable(factory) and not hasattr(factory, "create_storage_service"):
            return factory(storage_provider)

        if hasattr(factory, "create_storage_service"):
            return factory.create_storage_service(storage_provider)

        raise ValueError("Invalid storage service factory provided")

    def _build_destination_path(self, media_id: uuid.UUID, filename: str) -> str:
        return f"media/{media_id}/{filename}"

    def _extract_file_path(self, metadata: Optional[Dict[str, Any]], default_path: str) -> str:
        if isinstance(metadata, dict):
            return metadata.get("file_path", default_path)
        return default_path

    def _extract_file_size(self, metadata: Optional[Dict[str, Any]], file_data: bytes) -> int:
        if isinstance(metadata, dict) and "size" in metadata:
            return int(metadata["size"])
        return len(file_data)

