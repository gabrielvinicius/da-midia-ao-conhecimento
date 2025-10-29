# src/media_management/application/commands/create_media_command_handler.py
"""Command handler responsible for media creation workflows."""

from __future__ import annotations

import mimetypes
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict

import structlog

from src.media_management.domain.enums import MediaStatus, MediaType
from src.media_management.domain.media import Media
from src.shared.exceptions.domain_exceptions import ValidationError
from .components import (
    DefaultMediaEventPublisher,
    DefaultMediaMetricsPublisher,
    DefaultMediaUploadSideEffectPublisher,
    DefaultStorageServiceResolver,
    DefaultStorageUploader,
    DefaultUploadMetadataMapper,
    FileSizeMediaFileValidator,
    MediaFileValidator,
    MediaUploadSideEffectPublisher,
    StorageUploader,
    UploadMetadataMapper,
)
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
        storage_uploader: StorageUploader,
        metadata_mapper: UploadMetadataMapper,
        side_effect_publisher: MediaUploadSideEffectPublisher,
        file_validator: MediaFileValidator,
    ) -> None:
        self.media_repository = media_repository
        self.storage_uploader = storage_uploader
        self.metadata_mapper = metadata_mapper
        self.side_effect_publisher = side_effect_publisher
        self.file_validator = file_validator

    @classmethod
    def with_default_components(
        cls,
        media_repository: Any,
        storage_service_factory: Any,
        metrics_service: Any,
        *,
        event_bus: Any = None,
        emit_legacy_task: bool = True,
    ) -> "CreateMediaCommandHandler":
        """Build a handler with the default component implementations."""

        return cls(
            media_repository=media_repository,
            storage_uploader=DefaultStorageUploader(
                storage_resolver=DefaultStorageServiceResolver(factory=storage_service_factory)
            ),
            metadata_mapper=DefaultUploadMetadataMapper(),
            side_effect_publisher=DefaultMediaUploadSideEffectPublisher(
                metrics_publisher=DefaultMediaMetricsPublisher(metrics_service=metrics_service),
                event_publisher=DefaultMediaEventPublisher(
                    event_bus=event_bus,
                    emit_legacy_task=emit_legacy_task,
                ),
            ),
            file_validator=FileSizeMediaFileValidator(
                min_size_bytes=cls.MIN_FILE_SIZE_BYTES,
                max_size_bytes=cls.MAX_FILE_SIZE_BYTES,
            ),
        )

    async def handle(self, command: CreateMediaCommand) -> Media:
        """Execute the command returning the persisted media entity."""

        self.file_validator.validate(command.file, command.filename)
        media_type = self._detect_media_type(command.filename)
        content_type = self._guess_mime_type(command.filename)

        media_id = uuid.uuid4()
        upload_result = await self.storage_uploader.upload(
            command=command,
            media_id=media_id,
            content_type=content_type,
        )
        upload_metadata = self.metadata_mapper.map(
            upload_result.metadata,
            default_path=upload_result.destination_path,
            file_data=command.file,
        )

        media = Media.create(
            media_id=media_id,
            user_id=command.user_id,
            original_file_path=upload_metadata.stored_path,
            media_type=media_type,
            storage_provider=command.storage_provider,
            transcription_provider=command.transcription_provider,
            summarization_provider=command.summarization_provider,
            status=MediaStatus.UPLOADED,
        )

        media = media.update(
            filename=command.filename,
            file_size=upload_metadata.file_size,
            mime_type=content_type,
            created_at=datetime.now(timezone.utc),
        )

        saved_media = await self._persist_media(media)

        await self.side_effect_publisher.publish(saved_media, upload_metadata)

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

    def _detect_media_type(self, filename: str) -> MediaType:
        _, ext = os.path.splitext(filename or "")
        media_type = self._MEDIA_TYPE_MAP.get(ext.lower())
        if not media_type:
            raise ValidationError("filename", filename, "Unsupported file type")
        return media_type

    def _guess_mime_type(self, filename: str) -> str:
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"

