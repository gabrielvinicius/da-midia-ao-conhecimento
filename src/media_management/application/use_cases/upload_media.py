"""Envio de uma mídia: valida, grava o arquivo, registra e anuncia."""
from __future__ import annotations

import mimetypes
import os
import uuid
from typing import Any, Dict, Optional, Set

import structlog

from src.media_management.application.dtos import CreateMediaCommand
from src.media_management.application.ports import (
    EventBusPort,
    MediaRepositoryPort,
    StorageUploaderPort,
    UploadMetadataMapperPort,
)
from src.media_management.application.services.components import (
    DefaultMediaUploadSideEffectPublisher,
    MediaEventPublisher,
    MediaMetricsPublisher,
)
from src.media_management.application.services.validators import MediaUploadValidator
from src.media_management.config.settings import media_settings
from src.media_management.domain import Media
from src.media_management.domain.enums import MediaType
from src.media_management.application.errors import InvalidUploadError

logger = structlog.get_logger(__name__)


_MEDIA_TYPE_BY_EXTENSION: Dict[str, MediaType] = {
    **{ext: MediaType.AUDIO for ext in (".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a")},
    **{ext: MediaType.VIDEO for ext in (".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv")},
    # Documentos e imagens viram texto (extração ou OCR).
    **{ext: MediaType.TEXT for ext in (".txt", ".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".tiff", ".bmp")},
}


def media_type_of(filename: str) -> MediaType:
    _, ext = os.path.splitext(filename or "")
    media_type = _MEDIA_TYPE_BY_EXTENSION.get(ext.lower())
    if not media_type:
        raise InvalidUploadError("Formato de arquivo não suportado")
    return media_type


class UploadMedia:
    def __init__(
        self,
        media_repository: MediaRepositoryPort,
        storage_uploader: StorageUploaderPort,
        metadata_mapper: UploadMetadataMapperPort,
        upload_validator: MediaUploadValidator,
        event_bus: Optional[EventBusPort] = None,
        metrics: Any = None,
    ) -> None:
        self._media = media_repository
        self._uploader = storage_uploader
        self._metadata_mapper = metadata_mapper
        self._upload_validator = upload_validator
        self.side_effect_publisher = DefaultMediaUploadSideEffectPublisher(
            metrics_publisher=MediaMetricsPublisher(metrics_service=metrics),
            event_publisher=MediaEventPublisher(event_bus=event_bus),
        )
        # Provedores conhecidos por campo.
        self._allowed: Dict[str, Set[str]] = {
            "storage_provider": set(media_settings.storage_providers_allowed or []),
            "transcription_provider": set(media_settings.transcription_providers_allowed or []),
        }

    async def execute(self, command: CreateMediaCommand) -> Media:
        self._upload_validator.validate(command.file_size_bytes, command.filename)
        self._check_providers(command)

        media_type = media_type_of(command.filename)
        content_type = mimetypes.guess_type(command.filename)[0] or "application/octet-stream"
        media_id = uuid.uuid4()

        upload_result = await self._uploader.upload(
            command=command, media_id=media_id, content_type=content_type
        )
        upload_metadata = self._metadata_mapper.map(
            upload_result.metadata,
            default_path=upload_result.destination_path,
            file_size=command.file_size_bytes,
        )
        media = Media.create(
            media_id=media_id,
            user_id=command.user_id,
            filename=command.filename,
            file_size_bytes=upload_metadata.file_size,
            mime_type=content_type,
            media_type=media_type,
            storage_provider=command.storage_provider,
            original_file_path=upload_metadata.stored_path,
            transcription_provider=command.transcription_provider,
            language="auto",
        )
        try:
            saved = await self._media.save(media)
        except Exception:
            # Sem o registro, o arquivo ficaria órfão no armazenamento (era a
            # única origem de órfãos; a exclusão já não deixa sobras).
            await self._discard_upload(command, upload_metadata.stored_path)
            raise
        await self.side_effect_publisher.publish(saved, upload_metadata, command.correlation_id)
        logger.info("media_management.create_media.completed", media_id=str(saved.id), user_id=str(saved.user_id))
        return saved

    async def _discard_upload(self, command: CreateMediaCommand, path: str) -> None:
        try:
            await self._uploader.discard(command, path)
        except Exception as exc:  # a falha original é a que importa
            logger.warning("media_management.upload_discard_failed", path=path, error=str(exc))

    def _check_providers(self, command: CreateMediaCommand) -> None:
        """Armazenamento desconhecido é recusado (400): antes, só gerava um aviso
        no log e o envio terminava em erro 500 ao procurar o armazenamento.
        Um modelo de transcrição desconhecido só gera aviso: o worker usa o padrão."""
        storage = command.storage_provider
        allowed_storage = self._allowed["storage_provider"]
        if allowed_storage and storage not in allowed_storage:
            raise InvalidUploadError(
                f"Armazenamento desconhecido: {storage}. Opções: {', '.join(sorted(allowed_storage))}."
            )
        transcription = command.transcription_provider
        allowed_transcription = self._allowed["transcription_provider"]
        if transcription and allowed_transcription and transcription not in allowed_transcription:
            logger.warning(
                "media_management.provider.unrecognized",
                field="transcription_provider", provider=transcription, allowed=sorted(allowed_transcription),
            )


__all__ = ["UploadMedia", "media_type_of"]
