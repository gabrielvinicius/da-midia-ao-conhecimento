"""Media Service Application Service.

Combines command and query operations for Media entities.
"""

from __future__ import annotations

import contextlib
import mimetypes
import os
import re
import time
import uuid
from typing import Any, Dict, Optional, Sequence, Set

import structlog

from src.media_management.application.errors import MediaDataErasureError
from src.media_management.application.policies import MediaAccessPolicy
from src.media_management.application.upload_events import upload_event_for
from src.shared.application.unit_of_work import UnitOfWorkPort
from src.media_management.application.ports import (
    EventBusPort,
    MediaMetricsPort,
    MediaRepositoryPort,
    StorageDownloaderPort,
    StorageUploaderPort,
    MediaDataEraserPort,
    StoredFileRemoverPort,
    UploadMetadataMapperPort,
)
from src.media_management.application.services.components import (
    DefaultMediaUploadSideEffectPublisher,
    FileSizeMediaFileValidator,
    MediaEventPublisher,
    MediaMetricsPublisher,
)
from src.media_management.config.settings import media_settings
from src.media_management.domain import Media
from src.media_management.domain.enums import MediaType
from src.shared.domain.errors import ValidationError
from src.shared.domain.events import (
    MediaDeleted,
    MediaReprocessRequested,
)
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

logger = structlog.get_logger(__name__)

RANGE_HEADER_PATTERN = re.compile(r"bytes=(\d+)-(\d+)?")


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
        ".png": MediaType.TEXT,
        ".jpg": MediaType.TEXT,
        ".jpeg": MediaType.TEXT,
        ".tiff": MediaType.TEXT,
        ".bmp": MediaType.TEXT,
    }

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
    ) -> None:
        self.media_repository = media_repository
        self.storage_uploader = storage_uploader
        self.metadata_mapper = metadata_mapper
        self.metrics = metrics_service
        self.upload_validator = upload_validator
        self.media_read_service = media_read_service
        self.event_bus = event_bus
        self.storage_downloader = storage_downloader
        self._unit_of_work = unit_of_work

        # Provider allowlists per bounded context (soft validation: warn if unknown)
        self._allowed_storage_providers: Set[str] = set(
            media_settings.storage_providers_allowed or []
        )
        self._allowed_transcription = set(
            media_settings.transcription_providers_allowed or []
        )
        self._allowed_summarization = set(
            media_settings.summarization_providers_allowed or []
        )
        self._allowed_sentiment = set(media_settings.sentiment_providers_allowed or [])
        self._allowed_topic = set(media_settings.topic_providers_allowed or [])

        self.side_effect_publisher = DefaultMediaUploadSideEffectPublisher(
            metrics_publisher=MediaMetricsPublisher(metrics_service=metrics_service),
            event_publisher=MediaEventPublisher(event_bus=event_bus),
        )
        self.file_validator = FileSizeMediaFileValidator(
            min_size_bytes=self.MIN_FILE_SIZE_BYTES,
            max_size_bytes=self.MAX_FILE_SIZE_BYTES,
        )

        # Components for Maintenance
        self.access_policy = MediaAccessPolicy()
        self.storage_maintenance = storage_maintenance
        # Um por módulo que guarda dados derivados da mídia, na ordem de exclusão.
        self.data_erasers = list(data_erasers)

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
                command.storage_provider,
                self._allowed_storage_providers,
                "storage_provider",
            ),
            transcription_provider=self._validate_provider(
                command.transcription_provider,
                self._allowed_transcription,
                "transcription_provider",
            ),
            summarization_provider=self._validate_provider(
                command.summarization_provider,
                self._allowed_summarization,
                "summarization_provider",
            ),
            sentiment_provider=self._validate_provider(
                command.sentiment_provider,
                self._allowed_sentiment,
                "sentiment_provider",
            ),
            topic_modeling_provider=self._validate_provider(
                command.topic_modeling_provider,
                self._allowed_topic,
                "topic_modeling_provider",
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
            filename=validated_command.filename,
            file_size_bytes=upload_metadata.file_size,
            mime_type=content_type,
            media_type=media_type,
            storage_provider=validated_command.storage_provider,
            original_file_path=upload_metadata.stored_path,
            transcription_provider=validated_command.transcription_provider,
            summarization_provider=validated_command.summarization_provider,
            sentiment_provider=validated_command.sentiment_provider,
            topic_modeling_provider=validated_command.topic_modeling_provider,
            language="auto",
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
            raise ValueError(f"Mídia {command.media_id} não encontrada")

        # Access Check
        effective_user = user_id
        if effective_user is None and user_role != UserRole.ADMIN:
            raise PermissionError(
                "User identifier is required for non-admin operations"
            )

        self.access_policy.ensure_can_access(media, effective_user, user_role)

        try:
            # Uma só transação: os dados de cada módulo e o registro da mídia
            # saem juntos. O arquivo é apagado antes da confirmação; se falhar,
            # nada é apagado do banco e a exclusão pode ser repetida.
            async with self._transaction():
                await self._delete_associated_records(media.id)
                await self._delete_original_file(media)
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
            logger.info(
                "media_management.delete_media.completed",
                media_id=str(media.id),
            )
            return media
        finally:
            if self.metrics and hasattr(self.metrics, "record_operation"):
                await self.metrics.record_operation(
                    operation="delete_media",
                    user_id=str(user_id) if user_id else "unknown",
                    status="success" if success else "failure",
                    duration=time.monotonic() - start_time,
                    media_id=str(media.id),
                    media_type="unknown",
                    provider=None,
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
            raise ValueError(f"Mídia {command.media_id} não encontrada")

        self.access_policy.ensure_can_access(media, user_id, user_role)
        # Verificado antes da limpeza: uma recusa não pode apagar resultados.
        media.ensure_can_be_reprocessed()

        try:
            # Os resultados anteriores saem e a mídia volta a "em processamento"
            # na mesma transação; os eventos só são publicados depois dela.
            async with self._transaction():
                await self._delete_associated_records(media.id)
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
                    upload_event_for(media, correlation_id=f"reprocess-{uuid.uuid4()}")
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
                    provider=None,
                )

    # ------------------------------------------------------------------ #
    # Ciclo de vida, conduzido pelos eventos do processamento
    # ------------------------------------------------------------------ #
    async def record_processing_started(self, media_id: uuid.UUID) -> Optional[Media]:
        return await self._transition(media_id, lambda media: media.mark_as_processing())

    async def record_text_ready(self, media_id: uuid.UUID) -> Optional[Media]:
        return await self._transition(media_id, lambda media: media.mark_as_completed())

    async def record_processing_failed(
        self, media_id: uuid.UUID, error_message: Optional[str]
    ) -> Optional[Media]:
        return await self._transition(
            media_id, lambda media: media.mark_as_failed(error_message or "Erro desconhecido")
        )

    async def _transition(self, media_id: uuid.UUID, change) -> Optional[Media]:
        """Carrega a mídia, aplica a regra da entidade e grava. None se não existir."""
        media = await self.media_repository.get_by_id(media_id)
        if not media:
            logger.error("media_management.media_not_found", media_id=str(media_id))
            return None
        change(media)
        await self.media_repository.update(media)
        return media

    async def get_media(self, query: GetMediaQuery) -> Optional[Media]:
        """Retrieves a single media entity."""
        return await self.media_read_service.get_media(query)

    async def list_media(self, query: ListMediaQuery):
        """Lists media entities with pagination and filtering."""
        return await self.media_read_service.list_media(query)

    async def get_media_statistics(
        self, query: GetMediaStatisticsQuery
    ) -> Dict[str, Any]:
        """Returns statistics about media entities."""
        return await self.media_read_service.get_media_statistics(query)

    async def get_media_stream(
        self,
        query: GetMediaStreamQuery,
        user_id: Optional[uuid.UUID] = None,
        user_role: Optional[UserRole] = None,
    ) -> MediaStreamDTO:
        """Obtém os bytes de uma mídia processando cabeçalhos de Range para streaming."""
        media = await self.media_repository.get_by_id(query.media_id)
        if not media:
            raise ValueError("Mídia não encontrada")

        self.access_policy.ensure_can_access(media, user_id, user_role)

        if not media.original_file_path:
            raise ValueError("Arquivo de mídia indisponível")

        if not self.storage_downloader:
            raise RuntimeError("Storage downloader not configured")

        provider = (getattr(media, "storage_provider", None) or "local").lower()
        try:
            file_bytes = await self.storage_downloader.download(provider, media.original_file_path)
        except Exception as exc:
            logger.error("media.stream.download_failed", media_id=str(media.id), error=str(exc))
            raise ValueError("Arquivo de mídia ausente no storage")

        file_size = len(file_bytes)
        if file_size == 0:
            raise ValueError("Arquivo de mídia vazio")

        filename = media.filename or media.original_file_path.split("/")[-1]
        mime_type = media.mime_type or "application/octet-stream"

        headers = {
            "Accept-Ranges": "bytes",
            "Content-Disposition": f'inline; filename="{filename}"',
        }

        range_header = query.range_header
        if range_header:
            range_header = range_header.strip()
            match = RANGE_HEADER_PATTERN.match(range_header)
            if not match:
                raise ValueError("Cabeçalho Range inválido")

            start = int(match.group(1))
            end = int(match.group(2)) if match.group(2) is not None else file_size - 1
            if start >= file_size:
                raise ValueError("Requested range not satisfiable")

            end = min(end, file_size - 1)
            payload = file_bytes[start : end + 1]
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            headers["Content-Length"] = str(len(payload))
            status_code = 206
        else:
            payload = file_bytes
            headers["Content-Length"] = str(file_size)
            status_code = 200

        return MediaStreamDTO(
            content=payload,
            media_type=mime_type,
            headers=headers,
            status_code=status_code,
        )

    # Private Helpers

    async def _persist_media(self, media: Media) -> Media:
        return await self.media_repository.save(media)

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
        self,
        name: str | None,
        allowed: Set[str],
        field: str,
    ) -> str | None:
        if name is None:
            return None
        if allowed and name not in allowed:
            logger.warning(
                "media_management.provider.unrecognized",
                field=field,
                provider=name,
                allowed=list(sorted(allowed)),
            )
        return name

    def _transaction(self):
        """Unidade de trabalho da operação (sem ela, cada repositório confirma a sua parte)."""
        if self._unit_of_work is None:
            return contextlib.nullcontext()
        return self._unit_of_work.transaction()

    async def _delete_associated_records(self, media_id: uuid.UUID) -> None:
        """Pede a cada módulo que apague o que derivou da mídia.

        Uma falha interrompe a operação e chega ao usuário: seguir adiante
        deixaria dados para trás (RNF06) ou, no reprocessamento, um registro
        antigo em conflito com o novo. Os apagadores são idempotentes, então a
        exclusão pode simplesmente ser repetida.
        """
        for eraser in self.data_erasers:
            try:
                await eraser.erase(media_id)
            except Exception as exc:
                logger.error(
                    "media.delete.erase_failed",
                    media_id=str(media_id),
                    module=getattr(eraser, "name", type(eraser).__name__),
                    error=str(exc),
                )
                raise MediaDataErasureError(
                    "Não foi possível apagar os dados derivados da mídia. "
                    "Nada foi perdido; tente novamente."
                ) from exc

    async def _delete_original_file(self, media: Media) -> None:
        file_path = getattr(media, "original_file_path", None)
        if not file_path:
            return
        
        provider = (getattr(media, "storage_provider", None) or "local").lower()
        if not self.storage_maintenance:
            logger.warning(
                "media.delete.storage_maintenance_missing",
                path=file_path,
                provider=provider,
            )
            return

        try:
            # Our path convention is user_id/year/month/media_id/filename
            # We want to delete the media_id folder to clean up derived files too.
            path_parts = file_path.split("/")
            if len(path_parts) >= 4:
                # user_id/year/month/media_id
                folder_path = "/".join(path_parts[:4])
                await self.storage_maintenance.delete_folder(provider, folder_path)
                logger.info("media.delete.folder_deleted", path=folder_path, provider=provider)
            else:
                # Fallback to single file delete if path doesn't match convention
                await self.storage_maintenance.delete_file(provider, file_path)
                logger.info("media.delete.file_deleted", path=file_path, provider=provider)
        except Exception as exc:
            # Um arquivo esquecido no disco é dado do usuário que fica (RNF06):
            # a exclusão para aqui, com a mídia ainda registrada, e pode ser repetida.
            logger.error(
                "media.delete.storage_cleanup_failed",
                path=file_path,
                provider=provider,
                error=str(exc),
            )
            raise MediaDataErasureError(
                "Não foi possível apagar o arquivo da mídia. Tente novamente."
            ) from exc
