# src/notifications/infrastructure/repositories/notification_repository.py
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.notifications.domain import Notification
from src.notifications.infrastructure.persistence.models import NotificationModel


class NotificationRepository:
    def __init__(self, db):
        self.db = db

    async def find_by_id(self, notification_id: str) -> Optional[Notification]:
        """Finds a notification by its ID."""
        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(
                select(NotificationModel).where(
                    NotificationModel.id == UUID(notification_id)
                )
            )
            model = result.scalar_one_or_none()
            return model.to_domain() if model else None
        return self.find_by_id_sync(notification_id)

    def find_by_id_sync(self, notification_id: str) -> Optional[Notification]:
        result = self.db.execute(
            select(NotificationModel).where(
                NotificationModel.id == UUID(notification_id)
            )
        )
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def save(self, notification: Notification) -> Notification:
        """Saves a notification to the database."""
        model = NotificationModel.from_domain(notification)
        if isinstance(self.db, AsyncSession):
            self.db.add(model)
            await self.db.commit()
            await self.db.refresh(model)
            return model.to_domain()
        return self.save_sync(notification)

    def save_sync(self, notification: Notification) -> Notification:
        model = NotificationModel.from_domain(notification)
        self.db.add(model)
        self.db.commit()
        self.db.refresh(model)
        return model.to_domain()

    async def list_by_user(self, user_id: str) -> List[Notification]:
        """Lists all notifications for a specific user."""
        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(
                select(NotificationModel).where(
                    NotificationModel.user_id == UUID(user_id)
                )
            )
            return [model.to_domain() for model in result.scalars().all()]
        return self.list_by_user_sync(user_id)

    def list_by_user_sync(self, user_id: str) -> List[Notification]:
        result = self.db.execute(
            select(NotificationModel).where(
                NotificationModel.user_id == UUID(user_id)
            )
        )
        return [model.to_domain() for model in result.scalars().all()]

    async def mark_as_read(self, notification_id: str) -> bool:
        """Marks a notification as read (sets opened_at)."""

        from src.shared.domain.time.clock import utcnow
        now = utcnow()

        if isinstance(self.db, AsyncSession):
            stmt = (
                update(NotificationModel)
                .where(NotificationModel.id == UUID(notification_id))
                .values(opened_at=now)
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount > 0
        return self.mark_as_read_sync(notification_id)

    def mark_as_read_sync(self, notification_id: str) -> bool:
        from src.shared.domain.time.clock import utcnow
        now = utcnow()

        stmt = (
            update(NotificationModel)
            .where(NotificationModel.id == UUID(notification_id))
            .values(opened_at=now)
        )
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount > 0

    async def delete(self, notification_id: str) -> bool:
        """Deletes a notification by its ID."""
        if isinstance(self.db, AsyncSession):
            # We need to find the MODEL to delete it
            result = await self.db.execute(
                select(NotificationModel).where(
                    NotificationModel.id == UUID(notification_id)
                )
            )
            model = result.scalar_one_or_none()

            if model:
                await self.db.delete(model)
                await self.db.commit()
                return True
            return False
        return self.delete_sync(notification_id)

    def delete_sync(self, notification_id: str) -> bool:
        # We need to find the MODEL to delete it
        result = self.db.execute(
            select(NotificationModel).where(
                NotificationModel.id == UUID(notification_id)
            )
        )
        model = result.scalar_one_or_none()

        if model:
            self.db.delete(model)
            self.db.commit()
            return True
        return False

    async def count_all(self) -> int:
        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(
                select(func.count()).select_from(NotificationModel)
            )
            return result.scalar_one()
        return self.count_all_sync()

    def count_all_sync(self) -> int:
        result = self.db.execute(select(func.count()).select_from(NotificationModel))
        return result.scalar_one()

    async def count_unread_all(self) -> int:
        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(
                select(func.count())
                .select_from(NotificationModel)
                .where(NotificationModel.opened_at.is_(None))
            )
            return result.scalar_one()
        return self.count_unread_all_sync()

    def count_unread_all_sync(self) -> int:
        result = self.db.execute(
            select(func.count())
            .select_from(NotificationModel)
            .where(NotificationModel.opened_at.is_(None))
        )
        return result.scalar_one()

    async def count_by_user_id(self, user_id: UUID) -> int:
        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(
                select(func.count())
                .select_from(NotificationModel)
                .where(NotificationModel.user_id == user_id)
            )
            return result.scalar_one()
        return self.count_by_user_id_sync(user_id)

    def count_by_user_id_sync(self, user_id: UUID) -> int:
        result = self.db.execute(
            select(func.count())
            .select_from(NotificationModel)
            .where(NotificationModel.user_id == user_id)
        )
        return result.scalar_one()

    async def count_unread_by_user_id(self, user_id: UUID) -> int:
        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(
                select(func.count())
                .select_from(NotificationModel)
                .where(NotificationModel.user_id == user_id)
                .where(NotificationModel.opened_at.is_(None))
            )
            return result.scalar_one()
        return self.count_unread_by_user_id_sync(user_id)

    def count_unread_by_user_id_sync(self, user_id: UUID) -> int:
        result = self.db.execute(
            select(func.count())
            .select_from(NotificationModel)
            .where(NotificationModel.user_id == user_id)
            .where(NotificationModel.opened_at.is_(None))
        )
        return result.scalar_one()

    async def delete_older_than(self, days_to_keep: int) -> int:
        """Delete notifications older than given number of days."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        if isinstance(self.db, AsyncSession):
            stmt = delete(NotificationModel).where(
                NotificationModel.created_at < cutoff
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount or 0
        return self.delete_older_than_sync(days_to_keep)

    def delete_older_than_sync(self, days_to_keep: int) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        stmt = delete(NotificationModel).where(NotificationModel.created_at < cutoff)
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount or 0
