"""Repositório das notificações (SQLAlchemy, sessão assíncrona)."""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, select, update

from src.notifications.domain import Notification
from src.notifications.domain.entities.notification import NotificationStatus
from src.notifications.infrastructure.persistence.models import NotificationModel
from src.shared.domain.time.clock import utcnow
from src.shared.infrastructure.database.unit_of_work import commit as uow_commit


class NotificationRepository:
    def __init__(self, db):
        self.db = db

    async def find_by_id(self, notification_id: str) -> Optional[Notification]:
        """Finds a notification by its ID."""
        result = await self.db.execute(
            select(NotificationModel).where(NotificationModel.id == UUID(notification_id))
        )
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def save(self, notification: Notification) -> Notification:
        """Insere ou atualiza (merge)."""
        merged = await self.db.merge(NotificationModel.from_domain(notification))
        await uow_commit(self.db)
        return merged.to_domain()

    async def list_by_user(self, user_id: str, limit: int = 50, unread_only: bool = False) -> List[Notification]:
        """Avisos mais recentes do usuário, do mais novo para o mais antigo.

        O filtro de não lidos fica na consulta: filtrado depois do limite, um
        aviso não lido mais antigo que os ``limit`` últimos sumia da lista.
        """
        stmt = select(NotificationModel).where(NotificationModel.user_id == UUID(user_id))
        if unread_only:
            stmt = stmt.where(NotificationModel.opened_at.is_(None))
        result = await self.db.execute(stmt.order_by(NotificationModel.created_at.desc()).limit(limit))
        return [model.to_domain() for model in result.scalars().all()]

    async def mark_all_as_read(self, user_id: str) -> int:
        now = utcnow()
        result = await self.db.execute(
            update(NotificationModel)
            .where(NotificationModel.user_id == UUID(user_id))
            .where(NotificationModel.opened_at.is_(None))
            .values(opened_at=now, status=NotificationStatus.READ, updated_at=now)
        )
        await uow_commit(self.db)
        return result.rowcount or 0

    async def delete_by_user(self, user_id: UUID) -> int:
        result = await self.db.execute(
            delete(NotificationModel).where(NotificationModel.user_id == user_id)
        )
        await uow_commit(self.db)
        return result.rowcount or 0

    async def mark_as_delivered(self, notification_id: str) -> bool:
        """Marca como entregue via realtime (WebSocket), setando delivered_at."""
        now = utcnow()
        stmt = (
            update(NotificationModel)
            .where(NotificationModel.id == UUID(notification_id))
            .where(NotificationModel.delivered_at.is_(None))
            .values(status=NotificationStatus.DELIVERED, delivered_at=now, updated_at=now)
        )
        result = await self.db.execute(stmt)
        await uow_commit(self.db)
        return (result.rowcount or 0) > 0
