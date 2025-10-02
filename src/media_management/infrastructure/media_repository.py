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

    async def list_by_user(self, user_id: str, page: int = 1, limit: int = 10) -> List[Media]:
        """Lists all media for a specific user with pagination."""
        query = select(Media).where(Media.user_id == UUID(user_id))
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def list_all(self, page: int = 1, limit: int = 10, search: Optional[str] = None) -> List[Media]:
        """Lists all media in the system with pagination and search."""
        query = select(Media)
        if search:
            query = query.where(Media.original_file_path.ilike(f"%{search}%"))
        
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()

    async def delete(self, media_id: UUID) -> bool:
        media = await self.find_by_id(str(media_id))
        if media:
            await self.db.delete(media)
            await self.db.commit()
            return True
        return False
