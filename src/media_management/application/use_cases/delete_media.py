"""Exclusão de uma mídia e de tudo o que foi derivado dela (RNF06)."""
from __future__ import annotations

import time
import uuid
from typing import Any, Optional

import structlog

from src.media_management.application.dtos import DeleteMediaCommand
from src.media_management.application.policies import MediaAccessPolicy
from src.media_management.application.ports import EventBusPort, MediaRepositoryPort
from src.media_management.domain import Media
from src.shared.domain.errors import AccessDeniedError, NotFoundError
from src.shared.domain.events import MediaDeleted
from src.shared.domain.roles import UserRole

from ._metrics import record_operation
from .media_cleanup import MediaDataCleanup

logger = structlog.get_logger(__name__)


class DeleteMedia:
    def __init__(
        self,
        media_repository: MediaRepositoryPort,
        cleanup: MediaDataCleanup,
        access_policy: MediaAccessPolicy,
        event_bus: Optional[EventBusPort] = None,
        metrics: Any = None,
    ) -> None:
        self._media = media_repository
        self._cleanup = cleanup
        self._access = access_policy
        self._event_bus = event_bus
        self._metrics = metrics

    async def execute(
        self,
        command: DeleteMediaCommand,
        user_id: Optional[uuid.UUID] = None,
        user_role: Optional[UserRole] = None,
    ) -> Media:
        started = time.monotonic()
        media = await self._media.get_by_id(command.media_id)
        if not media:
            raise NotFoundError(f"Mídia {command.media_id} não encontrada")
        if user_id is None and user_role != UserRole.ADMIN:
            raise AccessDeniedError("Usuário não identificado")
        self._access.ensure_can_access(media, user_id, user_role)

        success = False
        try:
            # Uma só transação: os dados de cada módulo e o registro da mídia
            # saem juntos. O arquivo é apagado antes da confirmação; se falhar,
            # nada é apagado do banco e a exclusão pode ser repetida.
            async with self._cleanup.transaction():
                await self._cleanup.erase_derived_data(media.id)
                await self._cleanup.delete_stored_files(media)
                await self._media.delete(media.id)

            if self._event_bus:
                await self._event_bus.publish(
                    MediaDeleted(
                        media_id=str(media.id),
                        user_id=str(media.user_id),
                        triggered_by="user" if user_id else "admin",
                        actor_id=str(user_id) if user_id else "admin",
                    )
                )
            success = True
            logger.info("media_management.delete_media.completed", media_id=str(media.id))
            return media
        finally:
            await record_operation(
                self._metrics, "delete_media",
                user_id=user_id, media_id=media.id, success=success, started=started,
            )
