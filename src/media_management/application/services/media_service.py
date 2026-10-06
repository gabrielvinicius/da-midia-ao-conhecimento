"""Fachada dos casos de uso das mídias.

Cada operação vive na sua classe (application/use_cases); esta fachada só as
reúne, para que as rotas, a administração e os handlers continuem usando um
único ponto de entrada.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, Optional, Sequence

from src.media_management.application.policies import MediaAccessPolicy
from src.media_management.application.ports import (
    EventBusPort,
    MediaDataEraserPort,
    MediaMetricsPort,
    MediaRepositoryPort,
    StorageDownloaderPort,
    StorageUploaderPort,
    StoredFileRemoverPort,
    UploadMetadataMapperPort,
)
from src.media_management.application.use_cases import (
    DeleteMedia,
    MediaDataCleanup,
    MediaLifecycle,
    ReprocessMedia,
    StreamMedia,
    UploadMedia,
)
from src.media_management.domain import Media
from src.shared.application.unit_of_work import UnitOfWorkPort
from src.shared.domain.errors import NotFoundError
from src.shared.domain.roles import UserRole

from ..dtos import (
    CreateMediaCommand,
    DeleteMediaCommand,
    GetMediaQuery,
    GetMediaStatisticsQuery,
    GetMediaStreamQuery,
    ListMediaQuery,
    MediaStreamDTO,
    ReprocessMediaCommand,
)
from .media_read_service import MediaReadService
from .validators import MediaUploadValidator


class MediaService:
    def __init__(
        self,
        media_repository: MediaRepositoryPort,
        storage_uploader: StorageUploaderPort,
        metadata_mapper: UploadMetadataMapperPort,
        metrics_service: MediaMetricsPort,
        upload_validator: MediaUploadValidator,
        media_read_service: MediaReadService,
        event_bus: EventBusPort | None = None,
        storage_maintenance: StoredFileRemoverPort | None = None,
        data_erasers: Sequence[MediaDataEraserPort] = (),
        storage_downloader: StorageDownloaderPort | None = None,
        unit_of_work: UnitOfWorkPort | None = None,
        access_policy: MediaAccessPolicy | None = None,
    ) -> None:
        self.media_repository = media_repository
        self.media_read_service = media_read_service
        self.event_bus = event_bus
        self.storage_uploader = storage_uploader
        self.storage_downloader = storage_downloader
        access_policy = access_policy or MediaAccessPolicy()
        self._access = access_policy
        cleanup = MediaDataCleanup(data_erasers, storage_maintenance, unit_of_work)
        self.data_erasers = cleanup.data_erasers

        self.upload = UploadMedia(
            media_repository, storage_uploader, metadata_mapper, upload_validator,
            event_bus=event_bus, metrics=metrics_service,
        )
        self.deletion = DeleteMedia(
            media_repository, cleanup, access_policy, event_bus=event_bus, metrics=metrics_service
        )
        self.reprocessing = ReprocessMedia(
            media_repository, cleanup, access_policy, event_bus=event_bus, metrics=metrics_service
        )
        self.lifecycle = MediaLifecycle(media_repository)
        self.streaming = StreamMedia(media_repository, access_policy, storage_downloader)

    # Comandos
    async def create_media(self, command: CreateMediaCommand) -> Media:
        return await self.upload.execute(command)

    async def delete_media(
        self,
        command: DeleteMediaCommand,
        user_id: Optional[uuid.UUID] = None,
        user_role: Optional[UserRole] = None,
    ) -> Media:
        return await self.deletion.execute(command, user_id=user_id, user_role=user_role)

    async def reprocess_media(
        self,
        command: ReprocessMediaCommand,
        user_id: Optional[uuid.UUID] = None,
        user_role: Optional[UserRole] = None,
    ) -> Media:
        return await self.reprocessing.execute(command, user_id=user_id, user_role=user_role)

    # Ciclo de vida, conduzido pelos eventos do processamento
    async def record_processing_started(self, media_id: uuid.UUID) -> Optional[Media]:
        return await self.lifecycle.record_processing_started(media_id)

    async def record_text_ready(self, media_id: uuid.UUID) -> Optional[Media]:
        return await self.lifecycle.record_text_ready(media_id)

    async def record_analysis_completed(self, media_id: uuid.UUID) -> Optional[Media]:
        return await self.lifecycle.record_analysis_completed(media_id)

    async def record_processing_failed(
        self, media_id: uuid.UUID, error_message: Optional[str]
    ) -> Optional[Media]:
        return await self.lifecycle.record_processing_failed(media_id, error_message)

    # Consultas
    async def get_media(self, query: GetMediaQuery) -> Optional[Media]:
        return await self.media_read_service.get_media(query)

    async def get_accessible_media(
        self, query: GetMediaQuery, user_id: uuid.UUID, user_role: Optional[UserRole]
    ) -> Media:
        """A mídia, se quem pede é o dono ou administrador; senão, 404."""
        media = await self.media_read_service.get_media(query)
        if media is None:
            raise NotFoundError("Mídia não encontrada")
        self._access.ensure_can_access(media, user_id, user_role)
        return media

    async def list_media(self, query: ListMediaQuery):
        return await self.media_read_service.list_media(query)

    async def get_media_statistics(self, query: GetMediaStatisticsQuery) -> Dict[str, Any]:
        return await self.media_read_service.get_media_statistics(query)

    async def get_media_stream(
        self,
        query: GetMediaStreamQuery,
        user_id: Optional[uuid.UUID] = None,
        user_role: Optional[UserRole] = None,
    ) -> MediaStreamDTO:
        return await self.streaming.execute(query, user_id=user_id, user_role=user_role)
