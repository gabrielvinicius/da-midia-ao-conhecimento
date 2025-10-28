# src/media_management/infrastructure/media_repository.py
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.domain.enums import MediaStatus
from src.media_management.domain.media import Media


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

    async def list_all(
        self,
        user_id: Optional[UUID] = None,
        status: Optional[MediaStatus] = None,
    ) -> List[Media]:
        """Return all media optionally filtered by user or status."""

        return await self.list_paginated(page=1, limit=10_000, user_id=user_id, status=status)

    async def list_paginated(
        self,
        page: int = 1,
        limit: int = 10,
        user_id: Optional[UUID] = None,
        status: Optional[MediaStatus] = None,
        search: Optional[str] = None,
    ) -> List[Media]:
        """Return a paginated collection of media entries."""

        stmt = select(Media)
        if user_id:
            stmt = stmt.where(Media.user_id == user_id)
        if status:
            stmt = stmt.where(Media.status == status)
        if search:
            stmt = stmt.where(Media.original_file_path.ilike(f"%{search}%"))

        offset = max(page - 1, 0) * limit
        stmt = stmt.order_by(Media.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_all(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(Media))
        return result.scalar_one()

    async def count_by_status(self, status: MediaStatus) -> int:
        stmt = select(func.count()).select_from(Media).where(Media.status == status)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def count_by_user(self, user_id: UUID) -> int:
        stmt = select(func.count()).select_from(Media).where(Media.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def count_by_user_and_status(self, user_id: UUID, status: MediaStatus) -> int:
        stmt = (
            select(func.count())
            .select_from(Media)
            .where(Media.user_id == user_id)
            .where(Media.status == status)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()