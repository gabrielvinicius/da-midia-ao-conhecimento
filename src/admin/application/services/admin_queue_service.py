"""Fila de processamento, vista pelo administrador.

O worker pesado processa uma mídia por vez (GPU); as demais esperam. Esta
consulta mostra quem está na frente, há quanto tempo cada mídia está na etapa
atual e as que parecem paradas, para o administrador agir antes do usuário
reclamar.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional
from uuid import UUID

from src.admin.application.ports import AdminUserReadPort, MediaAdminPort, QueueDepthPort
from src.media_management.application.dtos import ListMediaQuery
from src.media_management.domain.enums import MediaStatus
from src.shared.domain.time.clock import utcnow
from src.user_management.application.dtos import GetUserQuery

QUEUE_STATUSES = (MediaStatus.UPLOADED, MediaStatus.PROCESSING, MediaStatus.ANALYZING)

# Tempo numa etapa a partir do qual a mídia parece parada. Uma aula de duas
# horas leva minutos para transcrever e analisar; os limites só pegam o que
# deixou de andar (as varreduras periódicas acabam marcando como falha).
DEFAULT_STUCK_MINUTES: Dict[MediaStatus, float] = {
    MediaStatus.UPLOADED: 15,
    MediaStatus.PROCESSING: 120,
    MediaStatus.ANALYZING: 180,
}


@dataclass(frozen=True)
class QueueItem:
    position: int
    media_id: UUID
    filename: Optional[str]
    media_type: str
    status: str
    owner_email: Optional[str]
    created_at: datetime.datetime
    stage_since: datetime.datetime
    stage_seconds: float
    stuck: bool


@dataclass(frozen=True)
class QueueSnapshot:
    items: List[QueueItem]
    counts: Dict[str, int]
    broker: Optional[Dict[str, int]]
    truncated: bool


class OwnerDirectory:
    """E-mail dos donos das mídias, consultando cada usuário uma vez."""

    def __init__(self, users: AdminUserReadPort) -> None:
        self._users = users

    async def emails(self, user_ids: Iterable[UUID]) -> Dict[UUID, Optional[str]]:
        found: Dict[UUID, Optional[str]] = {}
        for user_id in set(user_ids):
            user = await self._users.get_user_by_id(GetUserQuery(user_id=user_id))
            found[user_id] = getattr(user, "email", None)
        return found


class AdminQueueService:
    def __init__(
        self,
        media: MediaAdminPort,
        users: AdminUserReadPort,
        queue_depth: Optional[QueueDepthPort] = None,
        *,
        limit: int = 100,
        stuck_minutes: Optional[Dict[MediaStatus, float]] = None,
    ) -> None:
        self._media = media
        self._owners = OwnerDirectory(users)
        self._queue_depth = queue_depth
        self._limit = limit
        self._stuck_minutes = stuck_minutes or DEFAULT_STUCK_MINUTES

    async def snapshot(self) -> QueueSnapshot:
        """Mídias em andamento, da mais antiga para a mais nova."""
        page = await self._media.list_media(
            ListMediaQuery(page=1, limit=self._limit, status=list(QUEUE_STATUSES), order="asc")
        )
        emails = await self._owners.emails(m.user_id for m in page.items)
        now = utcnow()
        items = [self._item(position, media, emails.get(media.user_id), now) for position, media in enumerate(page.items, 1)]
        counts = {status.value: 0 for status in QUEUE_STATUSES}
        for item in items:
            counts[item.status] += 1
        broker = await self._queue_depth.waiting_tasks() if self._queue_depth else None
        return QueueSnapshot(items=items, counts=counts, broker=broker, truncated=page.total > len(items))

    def _item(self, position: int, media, owner_email: Optional[str], now: datetime.datetime) -> QueueItem:
        # updated_at muda a cada troca de estado: é o início da etapa atual.
        stage_since = media.updated_at or media.created_at
        stage_seconds = max(0.0, (now - stage_since).total_seconds())
        limit = self._stuck_minutes.get(media.status)
        return QueueItem(
            position=position,
            media_id=media.id,
            filename=media.filename,
            media_type=media.media_type.value,
            status=media.status.value,
            owner_email=owner_email,
            created_at=media.created_at,
            stage_since=stage_since,
            stage_seconds=stage_seconds,
            stuck=limit is not None and stage_seconds > limit * 60,
        )


__all__ = ["AdminQueueService", "OwnerDirectory", "QueueItem", "QueueSnapshot"]
