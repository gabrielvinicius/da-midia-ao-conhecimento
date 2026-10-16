"""Envio em partes: o arquivo chega em várias requisições e, completo, segue
como um envio comum.

A Cloudflare recusa requisições acima de 100 MB; um vídeo de 500 MB não
passava pelo endereço público. Cada parte é gravada a partir de uma posição
(``offset``): repetir uma parte que falhou regrava o mesmo trecho, e o total
recebido diz ao navegador de onde continuar.
"""
from __future__ import annotations

import datetime
import uuid
from typing import AsyncIterator, Optional

import structlog

from src.media_management.application.dtos import CreateMediaCommand, StartUploadCommand
from src.media_management.application.errors import InvalidUploadError
from src.media_management.application.ports import StagedUpload, UploadStagingPort
from src.media_management.application.use_cases.upload_media import UploadMedia
from src.media_management.domain import Media
from src.shared.domain.errors import ConflictError, NotFoundError
from src.shared.domain.time.clock import utcnow

logger = structlog.get_logger(__name__)


class ResumableUpload:
    def __init__(
        self,
        staging: Optional[UploadStagingPort],
        upload: UploadMedia,
        part_max_bytes: int,
        keep_for: datetime.timedelta,
    ) -> None:
        self._staging = staging
        self._upload = upload
        self.part_max_bytes = part_max_bytes
        self._keep_for = keep_for

    def _require_staging(self) -> UploadStagingPort:
        if self._staging is None:
            raise NotFoundError("O envio em partes não está disponível.")
        return self._staging

    async def _owned(self, upload_id: uuid.UUID, user_id) -> StagedUpload:
        """O envio, se pertence a quem pede; senão, 404 (como as mídias)."""
        staged = await self._require_staging().get(upload_id)
        if staged is None or staged.user_id != str(user_id):
            raise NotFoundError("Envio não encontrado")
        return staged

    async def start(self, command: StartUploadCommand) -> StagedUpload:
        staging = self._require_staging()
        self._upload.check_request(
            command.size_bytes, command.filename, command.storage_provider, command.transcription_provider
        )
        # Envios abandonados (aba fechada, rede que não voltou) saem aqui, sem
        # depender de uma tarefa periódica.
        removed = await staging.remove_created_before(utcnow() - self._keep_for)
        if removed:
            logger.info("media_management.resumable_upload.expired_removed", count=removed)
        staged = StagedUpload(
            upload_id=uuid.uuid4(),
            user_id=str(command.user_id),
            filename=command.filename,
            size_bytes=command.size_bytes,
            storage_provider=command.storage_provider,
            transcription_provider=command.transcription_provider,
            created_at=utcnow(),
        )
        await staging.create(staged)
        return staged

    async def status(self, upload_id: uuid.UUID, user_id) -> StagedUpload:
        return await self._owned(upload_id, user_id)

    async def receive(self, upload_id: uuid.UUID, user_id, offset: int, chunks: AsyncIterator[bytes]) -> int:
        """Grava uma parte a partir de ``offset`` e devolve o total recebido."""
        staged = await self._owned(upload_id, user_id)
        if offset < 0 or offset > staged.received_bytes:
            # Um buraco no arquivo: o navegador consulta o total e continua dali.
            raise ConflictError(f"Parte fora de ordem: recebidos {staged.received_bytes} bytes.")
        max_bytes = min(self.part_max_bytes, staged.size_bytes - offset)
        return await self._require_staging().write(upload_id, offset, chunks, max_bytes)

    async def complete(self, upload_id: uuid.UUID, user_id, correlation_id: Optional[str]) -> Media:
        staged = await self._owned(upload_id, user_id)
        if staged.received_bytes != staged.size_bytes:
            raise InvalidUploadError(
                f"Envio incompleto: recebidos {staged.received_bytes} de {staged.size_bytes} bytes."
            )
        staging = self._require_staging()
        media = await self._upload.execute(
            CreateMediaCommand(
                user_id=staged.user_id,
                file_path=staging.file_path(upload_id),
                file_size_bytes=staged.size_bytes,
                filename=staged.filename,
                storage_provider=staged.storage_provider,
                transcription_provider=staged.transcription_provider,
                correlation_id=correlation_id,
                move_source=True,
            )
        )
        # Só depois do registro: se ele falhar, o arquivo volta para a área
        # temporária (StorageUploaderPort.discard), e a conclusão pode ser repetida.
        await staging.remove(upload_id)
        return media

    async def cancel(self, upload_id: uuid.UUID, user_id) -> None:
        await self._owned(upload_id, user_id)
        await self._require_staging().remove(upload_id)


__all__ = ["ResumableUpload"]
