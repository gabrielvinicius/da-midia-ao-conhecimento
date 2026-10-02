"""Repositório das notificações (SQLAlchemy, sessão assíncrona)."""
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, func, select, update

from src.notifications.domain import Notification
from src.notifications.domain.entities.notification import NotificationStatus
from src.notifications.infrastructure.persistence.models import NotificationModel
from src.shared.domain.time.clock import utcnow
from src.shared.infrastructure.database.unit_of_work import commit as uow_commit
from src.shared.infrastructure.database.unit_of_work import rollback as uow_rollback


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
        await uow_rollback(self.db)  # libera conexão
        merged = await self.db.merge(NotificationModel.from_domain(notification))
        await uow_commit(self.db)
        await self.db.refresh(merged)
        return merged.to_domain()

    async def list_by_user(self, user_id: str) -> List[Notification]:
        """Lists all notifications for a specific user."""
        result = await self.db.execute(
            select(NotificationModel).where(NotificationModel.user_id == UUID(user_id))
        )
        return [model.to_domain() for model in result.scalars().all()]

    async def mark_as_read(self, notification_id: str) -> bool:
        """Marks a notification as read (sets opened_at)."""
        stmt = (
            update(NotificationModel)
            .where(NotificationModel.id == UUID(notification_id))
            .values(opened_at=utcnow())
        )
        result = await self.db.execute(stmt)
        await uow_commit(self.db)
        return result.rowcount > 0

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

    async def list_undelivered_by_user(self, user_id: str, limit: int = 50) -> List[Notification]:
        """Lista notificações ainda não entregues via realtime."""
        stmt = (
            select(NotificationModel)
            .where(NotificationModel.user_id == UUID(user_id))
            .where(NotificationModel.delivered_at.is_(None))
            .order_by(NotificationModel.created_at.asc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return [model.to_domain() for model in result.scalars().all()]

    async def delete(self, notification_id: str) -> bool:
        """Deletes a notification by its ID."""
        result = await self.db.execute(
            select(NotificationModel).where(NotificationModel.id == UUID(notification_id))
        )
        model = result.scalar_one_or_none()
        if not model:
            return False
        await self.db.delete(model)
        await uow_commit(self.db)
        return True

    async def count_all(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(NotificationModel))
        return result.scalar_one()

    async def count_unread_all(self) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(NotificationModel)
            .where(NotificationModel.opened_at.is_(None))
        )
        return result.scalar_one()

    async def count_by_user_id(self, user_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(NotificationModel)
            .where(NotificationModel.user_id == user_id)
        )
        return result.scalar_one()

    async def count_unread_by_user_id(self, user_id: UUID) -> int:
        result = await self.db.execute(
            select(func.count())
            .select_from(NotificationModel)
            .where(NotificationModel.user_id == user_id)
            .where(NotificationModel.opened_at.is_(None))
        )
        return result.scalar_one()

    async def delete_older_than(self, days_to_keep: int) -> int:
        """Delete notifications older than given number of days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        result = await self.db.execute(
            delete(NotificationModel).where(NotificationModel.created_at < cutoff)
        )
        await uow_commit(self.db)
        return result.rowcount or 0
