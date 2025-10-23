# src/media_management/infrastructure/media_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from uuid import UUID

from src.media_management.domain.media import Media
from src.media_management.domain.enums import MediaStatus


class MediaRepository:
    """SQLAlchemy implementation of the media repository."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, media_id: UUID) -> Optional[Media]:
        result = await self.db.execute(select(Media).where(Media.id == media_id))
        return result.scalar_one_or_none()

    async def add(self, media: Media) -> None:
        self.db.add(media)
        await self.db.flush()

    async def update(self, media: Media) -> None:
        # For SQLAlchemy, just adding to session and flushing is usually enough for updates
        # if the object is already tracked or has a primary key.
        await self.db.flush()

    async def delete(self, media: Media) -> None:
        await self.db.delete(media)
        await self.db.flush()

    async def list_all(self, user_id: Optional[UUID] = None, status: Optional[MediaStatus] = None) -> List[Media]:
        stmt = select(Media)
        if user_id:
            stmt = stmt.where(Media.user_id == user_id)
        if status:
            stmt = stmt.where(Media.status == status)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())