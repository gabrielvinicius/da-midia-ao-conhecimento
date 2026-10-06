"""Apaga as mídias de um usuário que será excluído (UserDataEraserPort)."""
from __future__ import annotations

from uuid import UUID

from src.media_management.application.dtos import DeleteMediaCommand
from src.media_management.application.use_cases import DeleteMedia
from src.media_management.infrastructure.repositories.media_repository import MediaRepository


class UserMediaEraser:
    """Cada mídia sai pelo caso de uso de exclusão: arquivo, transcrição,
    análise e trechos indexados vão junto, como na exclusão feita pelo dono."""

    name = "media_management"

    def __init__(self, repository: MediaRepository, deletion: DeleteMedia) -> None:
        self._repository = repository
        self._deletion = deletion

    async def erase(self, user_id: UUID) -> None:
        for media_id in await self._repository.list_ids_by_user(user_id):
            await self._deletion.execute(DeleteMediaCommand(media_id=media_id), user_id=user_id)


__all__ = ["UserMediaEraser"]
