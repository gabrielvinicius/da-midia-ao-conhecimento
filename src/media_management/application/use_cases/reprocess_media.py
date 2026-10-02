"""Reprocessamento de uma mídia que falhou."""
from __future__ import annotations

import time
import uuid
from typing import Any, Optional

from src.media_management.application.dtos import ReprocessMediaCommand
from src.media_management.application.policies import MediaAccessPolicy
from src.media_management.application.ports import EventBusPort, MediaRepositoryPort
from src.media_management.application.upload_events import upload_event_for
from src.media_management.domain import Media
from src.shared.domain.errors import NotFoundError
from src.shared.domain.events import MediaReprocessRequested
from src.shared.domain.roles import UserRole

from ._metrics import record_operation
from .media_cleanup import MediaDataCleanup


class ReprocessMedia:
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
        command: ReprocessMediaCommand,
        user_id: Optional[uuid.UUID] = None,
        user_role: Optional[UserRole] = None,
    ) -> Media:
        started = time.monotonic()
        media = await self._media.get_by_id(command.media_id)
        if not media:
            raise NotFoundError(f"Mídia {command.media_id} não encontrada")
        self._access.ensure_can_access(media, user_id, user_role)
        # Verificado antes da limpeza: uma recusa não pode apagar resultados.
        media.ensure_can_be_reprocessed()

        success = False
        try:
            # Os resultados anteriores saem e a mídia volta a "em processamento"
            # na mesma transação; os eventos só são publicados depois dela.
            async with self._cleanup.transaction():
                await self._cleanup.erase_derived_data(media.id)
                media.process()
                await self._media.update(media)

            if self._event_bus:
                await self._event_bus.publish(
                    MediaReprocessRequested(
                        media_id=str(media.id),
                        triggered_by="user" if user_id else "admin",
                        actor_id=str(user_id) if user_id else "admin",
                    )
                )
                # O processamento recomeça como num envio novo.
                await self._event_bus.publish(
                    upload_event_for(media, correlation_id=f"reprocess-{uuid.uuid4()}")
                )
            success = True
            return media
        finally:
            await record_operation(
                self._metrics, "reprocess_media",
                user_id=user_id, media_id=media.id, success=success, started=started,
            )
