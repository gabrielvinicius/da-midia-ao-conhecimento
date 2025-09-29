# src/media_management/infrastructure/media_repository.py
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.domain.media import Media


class MediaRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save(self, media: Media) -> Media:
        """Saves a media entity to the database."""
        self.db.add(media)
        await self.db.commit()
        await self.db.refresh(media)
        return media

    async def find_by_id(self, media_id: str) -> Optional[Media]:
        """Finds a media entity by its ID."""
        result = await self.db.execute(
            select(Media).where(Media.id == UUID(media_id))
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: str) -> List[Media]:
        """Lists all media for a specific user."""
        result = await self.db.execute(
            select(Media).where(Media.user_id == UUID(user_id))
        )
        return result.scalars().all()
