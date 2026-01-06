"""SQLAlchemy-backed repository for media aggregates."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

import structlog
from datetime import datetime
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.domain import Media
from src.media_management.domain.enums import MediaStatus, MediaType

from ..mappers import MediaMapper
from ..persistence.models import MediaEntity

logger = structlog.get_logger(__name__)


class MediaRepository:
    """Persists :class:`Media` instances using SQLAlchemy."""

    def __init__(self, db: AsyncSession, mapper: Optional[MediaMapper] = None) -> None:
        self.db = db
        self._mapper = mapper or MediaMapper()

    async def get_by_id(self, media_id: UUID) -> Optional[Media]:
        await self.db.rollback()  # garante conexão livre
        result = await self.db.execute(
            select(MediaEntity).where(MediaEntity.id == media_id)
        )
        entity = result.scalar_one_or_none()
        if entity is None:
            return None
        return self._mapper.to_domain(entity)

    async def add(self, media: Media) -> Media:
        entity = self._mapper.to_entity(media)
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        persisted = self._mapper.to_domain(entity)
        return self._mapper.merge_transient_data(persisted, media)

    async def save(self, media: Media) -> Media:
        entity = self._mapper.to_entity(media)
        merged = await self.db.merge(entity)
        await self.db.commit()
        await self.db.refresh(merged)
        persisted = self._mapper.to_domain(merged)
        return self._mapper.merge_transient_data(persisted, media)

    async def update(self, media: Media) -> Media:
        return await self.save(media)

    async def delete(self, media_id: UUID) -> None:
        result = await self.db.execute(
            select(MediaEntity).where(MediaEntity.id == media_id)
        )
        entity = result.scalar_one_or_none()
        if entity is not None:
            await self.db.delete(entity)
            await self.db.commit()

    async def update_status(
        self,
        media_id: UUID,
        status: MediaStatus,
        *,
        error_message: Optional[str] = None,
    ) -> Media:
        await self.db.rollback()  # garante conexão livre
        result = await self.db.execute(
            select(MediaEntity).where(MediaEntity.id == media_id)
        )
        entity = result.scalar_one()
        entity.status = status
        entity.error_message = error_message
        entity.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(entity)
        aggregate = self._mapper.to_domain(entity)
        updated = aggregate.update(error_message=error_message)
        return updated

    async def list_paginated(
        self,
        *,
        page: int = 1,
        limit: int = 10,
        user_id: Optional[UUID] = None,
        status: Optional[MediaStatus] = None,
        search: Optional[str] = None,
        order: str = "desc",
    ) -> List[Media]:
        await self._ensure_clean()
        stmt = select(MediaEntity)
        if user_id is not None:
            stmt = stmt.where(MediaEntity.user_id == user_id)
        if status is not None:
            stmt = stmt.where(MediaEntity.status == status)
        if search:
            stmt = stmt.where(MediaEntity.original_file_path.ilike(f"%{search}%"))

        offset = max(page - 1, 0) * limit
        stmt = stmt.order_by(
            MediaEntity.created_at.desc() if order == "desc" else MediaEntity.created_at.asc()
        ).offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        return [self._mapper.to_domain(entity) for entity in result.scalars().all()]

    async def count_filtered(
        self,
        *,
        user_id: Optional[UUID] = None,
        status: Optional[MediaStatus] = None,
        search: Optional[str] = None,
    ) -> int:
        stmt = select(func.count()).select_from(MediaEntity)
        if user_id is not None:
            stmt = stmt.where(MediaEntity.user_id == user_id)
        if status is not None:
            stmt = stmt.where(MediaEntity.status == status)
        if search:
            stmt = stmt.where(MediaEntity.original_file_path.ilike(f"%{search}%"))
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def list_all(
        self,
        user_id: Optional[UUID] = None,
        status: Optional[MediaStatus] = None,
    ) -> List[Media]:
        await self._ensure_clean()
        return await self.list_paginated(
            page=1,
            limit=10_000,
            user_id=user_id,
            status=status,
        )

    async def count_all(self) -> int:
        await self._ensure_clean()
        result = await self.db.execute(select(func.count()).select_from(MediaEntity))
        return result.scalar_one()

    async def count_by_status(self, status: MediaStatus) -> int:
        await self._ensure_clean()
        stmt = (
            select(func.count())
            .select_from(MediaEntity)
            .where(MediaEntity.status == status)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def count_by_user(self, user_id: UUID) -> int:
        await self._ensure_clean()
        stmt = (
            select(func.count())
            .select_from(MediaEntity)
            .where(MediaEntity.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def count_by_user_and_status(self, user_id: UUID, status: MediaStatus) -> int:
        await self._ensure_clean()
        stmt = (
            select(func.count())
            .select_from(MediaEntity)
            .where(MediaEntity.user_id == user_id)
            .where(MediaEntity.status == status)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def count_by_type(self, media_type: MediaType) -> int:
        await self._ensure_clean()
        stmt = (
            select(func.count())
            .select_from(MediaEntity)
            .where(MediaEntity.media_type == media_type)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def count_by_user_and_type(self, user_id: UUID, media_type: MediaType) -> int:
        await self._ensure_clean()
        stmt = (
            select(func.count())
            .select_from(MediaEntity)
            .where(MediaEntity.user_id == user_id)
            .where(MediaEntity.media_type == media_type)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def get_existing_paths(self, paths: List[str]) -> set[str]:
        """Check which of the provided paths exist in the database."""
        await self._ensure_clean()
        if not paths:
            return set()
        
        # In a real scenario with huge lists, we might need to chunk this query too.
        # For now, assuming reasonable batch sizes from the caller.
        stmt = select(MediaEntity.original_file_path).where(
            MediaEntity.original_file_path.in_(paths)
        )
        result = await self.db.execute(stmt)
        return set(result.scalars().all())

    async def _ensure_clean(self) -> None:
        """Rolls back any pending transaction to avoid asyncpg state errors."""
        try:
            await self.db.rollback()
        except Exception as exc:
            # Best-effort cleanup; leave session as-is if rollback fails
            logger.warning(
                "media_repository.rollback_failed",
                error=str(exc),
                message="Failed to rollback pending transaction (best-effort cleanup)",
            )
