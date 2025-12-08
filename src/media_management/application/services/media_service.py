"""Media Service Application Service.

Combines command and query operations for Media entities.
"""

from __future__ import annotations

import mimetypes
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

import structlog

from src.media_management.application.services.components import (
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
from src.media_management.application.commands.dto import (
    CleanupOrphanedFilesCommand,
    CreateMediaCommand,
    DeleteMediaCommand,
    ReprocessMediaCommand,
)
from src.media_management.application.commands.validators import MediaUploadValidator
from src.media_management.application.policies import MediaAccessPolicy
from src.media_management.application.queries.dto import (
    GetMediaQuery,
    GetMediaStatisticsQuery,
    ListMediaQuery,
)
from src.media_management.domain.media import Media
from src.media_management.infrastructure.metrics import PrometheusMediaMetrics
from src.media_management.infrastructure.repositories import MediaRepository
from src.media_management.application.queries.media_queries import MediaQueries # Alias for MediaReadService
from src.providers.domain.interfaces import IProviderRegistry, ProviderType
from src.shared.domain.enums import MediaStatus, MediaType
from src.shared.infrastructure.event_bus import SupportsEventBus
from src.shared.domain.events import (
    MediaDeleted,
    MediaReprocessRequested,
    MediaUploaded,
)
from src.shared.domain.errors import ValidationError
from src.storage.application.maintenance_service import StorageMaintenanceService
from src.storage.infrastructure.dependencies import StorageServiceFactory
from src.user_management.domain.user import UserRole

logger = structlog.get_logger(__name__)


class MediaService:
    """Service for managing media entities (CRUD + Business Logic)."""

    MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # 500MB
    MIN_FILE_SIZE_BYTES = 1

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
        media_repository: MediaRepository,
        storage_service_factory: StorageServiceFactory,
        metrics_service: Any,
        upload_validator: MediaUploadValidator,
        media_read_service: MediaQueries, # New dependency
        event_bus: SupportsEventBus | None = None,
        emit_legacy_task: bool = True,
        provider_registry: IProviderRegistry | None = None,
    ) -> None:
        self.media_repository = media_repository
        self.storage_factory = storage_service_factory
        self.metrics = metrics_service
        self.upload_validator = upload_validator
        self.media_read_service = media_read_service # Assign new dependency
        self.event_bus = event_bus
        self.emit_legacy_task = emit_legacy_task
        self.provider_registry = provider_registry
        
        # Components for Creation
        self.storage_uploader = DefaultStorageUploader(
            storage_resolver=DefaultStorageServiceResolver(factory=storage_service_factory)
        )
        self.metadata_mapper = DefaultUploadMetadataMapper()
        self.side_effect_publisher = DefaultMediaUploadSideEffectPublisher(
            metrics_publisher=DefaultMediaMetricsPublisher(metrics_service=metrics_service),
            event_publisher=DefaultMediaEventPublisher(
                event_bus=event_bus,
                emit_legacy_task=emit_legacy_task,
            ),
        )
        self.file_validator = FileSizeMediaFileValidator(
            min_size_bytes=self.MIN_FILE_SIZE_BYTES,
            max_size_bytes=self.MAX_FILE_SIZE_BYTES,
        )
        
        # Components for Maintenance
        self.access_policy = MediaAccessPolicy()
        self.storage_maintenance = StorageMaintenanceService(storage_service_factory)

    async def create_media(self, command: CreateMediaCommand) -> Media:
        """Uploads and creates a new media entity."""
        # 1. Validate File Content/Size (Policy)
        self.upload_validator.validate(command.file, command.filename)
        self.file_validator.validate(command.file, command.filename)

        # 2. Validate Providers
        validated_command = CreateMediaCommand(
            user_id=command.user_id,
            file=command.file,
            filename=command.filename,
            storage_provider=self._validate_provider(
                command.storage_provider, ProviderType.STORAGE
            ),
            transcription_provider=self._validate_provider(
                command.transcription_provider, ProviderType.TRANSCRIPTION
            ),
            summarization_provider=self._validate_provider(
                command.summarization_provider, ProviderType.SUMMARIZATION
            ),
            sentiment_provider=self._validate_provider(
                command.sentiment_provider, ProviderType.SENTIMENT_ANALYSIS
            ),
            topic_modeling_provider=self._validate_provider(
                command.topic_modeling_provider, ProviderType.TOPIC_MODELING
            ),
            metadata=command.metadata,
        )

        # 3. Detect Type
        media_type = self._detect_media_type(validated_command.filename)
        content_type = self._guess_mime_type(validated_command.filename)
        media_id = uuid.uuid4()

        # 4. Upload to Storage
        upload_result = await self.storage_uploader.upload(
            command=validated_command,
            media_id=media_id,
            content_type=content_type,
        )

        # 5. Map Metadata
        upload_metadata = self.metadata_mapper.map(
            upload_result.metadata,
            default_path=upload_result.destination_path,
            file_data=validated_command.file,
        )

        # 6. Create Entity
        media = Media.create(
            media_id=media_id,
            user_id=validated_command.user_id,
            original_file_path=upload_metadata.stored_path,
            media_type=media_type,
            storage_provider=validated_command.storage_provider,
            transcription_provider=validated_command.transcription_provider,
            summarization_provider=validated_command.summarization_provider,
            sentiment_provider=validated_command.sentiment_provider,
            topic_modeling_provider=validated_command.topic_modeling_provider,
            status=MediaStatus.UPLOADED,
        )
        media = media.update(
            filename=validated_command.filename,
            file_size=upload_metadata.file_size,
            mime_type=content_type,
            created_at=datetime.now(timezone.utc),
        )

        # 7. Persist
        saved_media = await self._persist_media(media)

        # 8. Publish Events/Metrics
        await self.side_effect_publisher.publish(saved_media, upload_metadata)

        logger.info(
            "media_management.create_media.completed",
            media_id=str(saved_media.id),
            user_id=str(saved_media.user_id),
        )
        return saved_media

    async def delete_media(
        self,
        command: DeleteMediaCommand,
        user_id: Optional[uuid.UUID] = None,
        user_role: Optional[UserRole] = None,
    ) -> Media:
        """Deletes a media entity and its associated files."""
        start_time = time.monotonic()
        success = False

        media = await self.media_repository.get_by_id(command.media_id)
        if not media:
            raise ValueError(f"Media {command.media_id} not found")

        # Access Check
        effective_user = user_id
        if effective_user is None and user_role != UserRole.ADMIN:
            raise PermissionError("User identifier is required for non-admin operations")

        self.access_policy.ensure_can_access(media, effective_user, user_role)

        try:
            # Delete associated records
            await self._delete_associated_records(media.id)

            # Delete file from storage
            await self._delete_original_file(media)

            # Delete from DB
            await self.media_repository.delete(media.id)

            # Publish Event
            if self.event_bus:
                triggered_by = "user" if user_id else "admin"
                actor_id = str(user_id) if user_id else "admin"
                await self.event_bus.publish(
                    MediaDeleted(
                        media_id=str(media.id),
                        user_id=str(media.user_id),
                        triggered_by=triggered_by,
                        actor_id=actor_id,
                    )
                )

            success = True
            logger.info("media_management.delete_media.completed", media_id=str(media.id))
            return media
        finally:
            if self.metrics and hasattr(self.metrics, "record_operation"):
                await self.metrics.record_operation(
                    operation="delete_media",
                    user_id=str(user_id) if user_id else "unknown",
                    status="success" if success else "failure",
                    duration=time.monotonic() - start_time,
                    media_id=str(media.id),
                    media_type="unknown", # Missing in original code but required by metrics
                    provider=None
                )

    async def reprocess_media(
        self,
        command: ReprocessMediaCommand,
        user_id: Optional[uuid.UUID] = None,
        user_role: Optional[UserRole] = None,
    ) -> Media:
        """Triggers reprocessing of a media item."""
        start_time = time.monotonic()
        success = False

        media = await self.media_repository.get_by_id(command.media_id)
        if not media:
            raise ValueError(f"Media {command.media_id} not found")

        self.access_policy.ensure_can_access(media, user_id, user_role)

        try:
            media.process()
            await self.media_repository.update(media)

            # Publish Reprocess Requested Event
            if self.event_bus:
                await self.event_bus.publish(
                    MediaReprocessRequested(
                        media_id=str(media.id),
                        triggered_by="user" if user_id else "admin",
                        actor_id=str(user_id) if user_id else "admin",
                    )
                )
                # Also publish MediaUploaded to trigger the pipeline again
                await self.event_bus.publish(
                    MediaUploaded(
                        media_id=str(media.id),
                        user_id=str(media.user_id),
                        filename=media.filename,
                        storage_provider=media.storage_provider,
                        media_type=media.media_type.value
                        if hasattr(media.media_type, "value")
                        else media.media_type,
                        file_size_bytes=media.file_size,
                        transcription_provider=media.transcription_provider,
                        summarization_provider=media.summarization_provider,
                        sentiment_provider=media.sentiment_provider,
                        topic_modeling_provider=media.topic_modeling_provider,
                        language=media.language,
                        correlation_id=f"reprocess-{uuid.uuid4()}",
                    )
                )

            success = True
            return media
        finally:
            if self.metrics and hasattr(self.metrics, "record_operation"):
                await self.metrics.record_operation(
                    operation="reprocess_media",
                    user_id=str(user_id) if user_id else "unknown",
                    status="success" if success else "failure",
                    duration=time.monotonic() - start_time,
                    media_id=str(media.id),
                    media_type="unknown",
                    provider=None
                )

    async def cleanup_orphaned_files(self, command: CleanupOrphanedFilesCommand) -> int:
        """Removes files from storage that are not referenced in the DB."""
        # 1. Gather all known paths
        provider_records: Dict[str, Set[str]] = {}
        page = 1
        page_size = 500
        
        while True:
            batch = await self.media_repository.list_paginated(page=page, limit=page_size)
            if not batch:
                break
            for media in batch:
                provider = (media.storage_provider or "local").lower()
                if provider not in provider_records:
                    provider_records[provider] = set()
                provider_records[provider].add(media.original_file_path)
            if len(batch) < page_size:
                break
            page += 1

        # 2. Cleanup
        total_deleted = 0
        providers = set(provider_records.keys())
        if not providers:
            providers.add("local")

        for provider in providers:
            known_files = provider_records.get(provider, set())
            deleted = await self.storage_maintenance.cleanup_orphaned_files(
                provider_name=provider,
                valid_files=known_files,
            )
            total_deleted += deleted
            logger.info(
                "media_management.cleanup.provider_summary",
                provider=provider,
                deleted=deleted,
                actor_id=command.actor_id,
            )

        return total_deleted

    async def get_media(self, query: GetMediaQuery) -> Optional[Media]:
        """Retrieves a single media entity."""
        return await self.media_read_service.get_media(query)

    async def list_media(self, query: ListMediaQuery) -> List[Media]:
        """Lists media entities with pagination and filtering."""
        return await self.media_read_service.list_media(query)

    async def get_media_statistics(self, query: GetMediaStatisticsQuery) -> Dict[str, Any]:
        """Returns statistics about media entities."""
        return await self.media_read_service.get_media_statistics(query)

    # Private Helpers

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

    def _validate_provider(
        self, name: str | None, provider_type: ProviderType
    ) -> str | None:
        if not name or self.provider_registry is None:
            return name
        active = {
            getattr(p, "name", None) or getattr(p, "get_name", lambda: None)()
            for p in self.provider_registry.get_active_providers(provider_type)
        }
        if name not in active:
            raise ValidationError(
                "provider", name, f"Provider not active for {provider_type.value}"
            )
        return name

    async def _delete_associated_records(self, media_id: uuid.UUID) -> None:
        db = getattr(self.media_repository, "db", None)
        if db is None:
            return
        from src.media_processing.infrastructure.transcription.transcription_repository import (
            TranscriptionRepository,
        )
        transcription_repo = TranscriptionRepository(db)
        try:
            await transcription_repo.delete_by_media_id(media_id)
        except Exception as exc:
            logger.warning(
                "media.delete.transcription_failed",
                media_id=str(media_id),
                error=str(exc),
            )

    async def _delete_original_file(self, media: Media) -> None:
        file_path = getattr(media, "original_file_path", None)
        if not file_path:
            return
        provider = (getattr(media, "storage_provider", None) or "local").lower()
        try:
            storage_client = self.storage_factory.create_storage_service(provider)
            await storage_client.delete(file_path)
        except Exception as exc:
            logger.warning(
                "media.delete.file_failed",
                path=file_path,
                provider=provider,
                error=str(exc),
            )
