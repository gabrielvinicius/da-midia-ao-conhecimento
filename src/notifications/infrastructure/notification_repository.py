from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.notifications.domain.notification import Notification


class NotificationRepository:
    def __init__(self, db):
        self.db = db

    async def find_by_id(self, notification_id: str) -> Optional[Notification]:
        """Finds a notification by its ID."""
        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(
                select(Notification).where(Notification.id == UUID(notification_id))
            )
            return result.scalar_one_or_none()
        return self.find_by_id_sync(notification_id)

    def find_by_id_sync(self, notification_id: str) -> Optional[Notification]:
        result = self.db.execute(
            select(Notification).where(Notification.id == UUID(notification_id))
        )
        return result.scalar_one_or_none()

    async def save(self, notification: Notification) -> Notification:
        """Saves a notification to the database."""
        if isinstance(self.db, AsyncSession):
            self.db.add(notification)
            await self.db.commit()
            await self.db.refresh(notification)
            return notification
        return self.save_sync(notification)

    def save_sync(self, notification: Notification) -> Notification:
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    async def list_by_user(self, user_id: str) -> List[Notification]:
        """Lists all notifications for a specific user."""
        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(
                select(Notification).where(Notification.user_id == UUID(user_id))
            )
            return result.scalars().all()
        return self.list_by_user_sync(user_id)

    def list_by_user_sync(self, user_id: str) -> List[Notification]:
        result = self.db.execute(
            select(Notification).where(Notification.user_id == UUID(user_id))
        )
        return result.scalars().all()

    async def mark_as_read(self, notification_id: str) -> bool:
        """Marks a notification as read."""
        if isinstance(self.db, AsyncSession):
            stmt = (
                update(Notification)
                .where(Notification.id == UUID(notification_id))
                .values(read=True)
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            return result.rowcount > 0
        return self.mark_as_read_sync(notification_id)

    def mark_as_read_sync(self, notification_id: str) -> bool:
        stmt = (
            update(Notification)
            .where(Notification.id == UUID(notification_id))
            .values(read=True)
        )
        result = self.db.execute(stmt)
        self.db.commit()
        return result.rowcount > 0

    async def delete(self, notification_id: str) -> bool:
        """Deletes a notification by its ID."""
        if isinstance(self.db, AsyncSession):
            notification = await self.find_by_id(notification_id)
            if notification:
                await self.db.delete(notification)
                await self.db.commit()
                return True
            return False
        return self.delete_sync(notification_id)

    def delete_sync(self, notification_id: str) -> bool:
        notification = self.find_by_id_sync(notification_id)
        if notification:
            self.db.delete(notification)
            self.db.commit()
            return True
        return False
