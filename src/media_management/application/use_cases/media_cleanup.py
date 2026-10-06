"""Remoção do que foi derivado de uma mídia (exclusão e reprocessamento)."""
from __future__ import annotations

import contextlib
import uuid
from typing import Optional, Sequence

import structlog

from src.media_management.application.errors import MediaDataErasureError
from src.media_management.application.ports import MediaDataEraserPort, StoredFileRemoverPort
from src.media_management.domain import Media
from src.shared.application.unit_of_work import UnitOfWorkPort

logger = structlog.get_logger(__name__)


class MediaDataCleanup:
    def __init__(
        self,
        data_erasers: Sequence[MediaDataEraserPort] = (),
        storage_maintenance: Optional[StoredFileRemoverPort] = None,
        unit_of_work: Optional[UnitOfWorkPort] = None,
    ) -> None:
        # Um por módulo que guarda dados derivados da mídia, na ordem de exclusão.
        self.data_erasers = list(data_erasers)
        self._storage = storage_maintenance
        self._unit_of_work = unit_of_work

    def transaction(self):
        """Unidade de trabalho da operação (sem ela, cada repositório confirma a sua parte)."""
        if self._unit_of_work is None:
            return contextlib.nullcontext()
        return self._unit_of_work.transaction()

    async def erase_derived_data(self, media_id: uuid.UUID) -> None:
        """Pede a cada módulo que apague o que derivou da mídia.

        Uma falha interrompe a operação e chega ao usuário: seguir adiante
        deixaria dados para trás (RNF06) ou, no reprocessamento, um registro
        antigo em conflito com o novo. Os apagadores são idempotentes, então a
        operação pode simplesmente ser repetida.
        """
        for eraser in self.data_erasers:
            try:
                await eraser.erase(media_id)
            except Exception as exc:  # qualquer falha do módulo vira "tente de novo"
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

    async def delete_stored_files(self, media: Media) -> None:
        """Apaga a pasta da mídia (convenção user/ano/mês/mídia/arquivo) ou o arquivo."""
        file_path = media.original_file_path
        if not file_path:
            return
        provider = (media.storage_provider or "local").lower()
        if not self._storage:
            logger.warning("media.delete.storage_maintenance_missing", path=file_path, provider=provider)
            return
        parts = file_path.split("/")
        try:
            if len(parts) >= 4:
                await self._storage.delete_folder(provider, "/".join(parts[:4]))
            else:
                await self._storage.delete_file(provider, file_path)
        except Exception as exc:  # qualquer falha do armazenamento vira "tente de novo"
            # Um arquivo esquecido no disco é dado do usuário que fica (RNF06):
            # a exclusão para aqui, com a mídia ainda registrada, e pode ser repetida.
            logger.error("media.delete.storage_cleanup_failed", path=file_path, provider=provider, error=str(exc))
            raise MediaDataErasureError(
                "Não foi possível apagar o arquivo da mídia. Tente novamente."
            ) from exc
