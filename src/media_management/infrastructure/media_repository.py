# src/media_management/infrastructure/media_repository.py
from typing import Optional, List, Tuple
from uuid import UUID
from sqlalchemy import select, desc, func
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
        """Lists all media for a specific user, ordered by creation date."""
        result = await self.db.execute(
            select(Media).where(Media.user_id == UUID(user_id)).order_by(desc(Media.created_at))
        )
        return result.scalars().all()

    async def list_all(self, page: int, limit: int, search: Optional[str] = None) -> Tuple[List[Media], int]:
        """Lists all media in the system with pagination and search. For admin use."""
        # Base query
        stmt = select(Media)
        if search:
            stmt = stmt.where(Media.original_file_path.ilike(f"%{search}%"))

        # Get total count for pagination metadata
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_items_result = await self.db.execute(count_stmt)
        total_items = total_items_result.scalar_one()

        # Get paginated items
        paginated_stmt = stmt.offset((page - 1) * limit).limit(limit).order_by(desc(Media.created_at))
        items_result = await self.db.execute(paginated_stmt)
        items = items_result.scalars().all()

        return items, total_items
