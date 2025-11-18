"""SQLAlchemy-backed repository for media aggregates."""

from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.domain.enums import MediaStatus
from src.media_management.domain.model import MediaAggregate
from src.media_management.application.notifications import enqueue_media_status_notification
import structlog

from .media_entity import MediaEntity
from .media_mapper import MediaMapper

logger = structlog.get_logger(__name__)


class MediaRepository:
    """Persists :class:`MediaAggregate` instances using SQLAlchemy."""

    def __init__(self, db: AsyncSession, mapper: Optional[MediaMapper] = None) -> None:
        self.db = db
        self._mapper = mapper or MediaMapper()

    async def get_by_id(self, media_id: UUID) -> Optional[MediaAggregate]:
        result = await self.db.execute(select(MediaEntity).where(MediaEntity.id == media_id))
        entity = result.scalar_one_or_none()
        if entity is None:
            return None
        return self._mapper.to_domain(entity)

    async def add(self, media: MediaAggregate) -> MediaAggregate:
        entity = self._mapper.to_entity(media)
        self.db.add(entity)
        await self.db.flush()
        persisted = self._mapper.to_domain(entity)
        return self._mapper.merge_transient_data(persisted, media)

    async def save(self, media: MediaAggregate) -> MediaAggregate:
        entity = self._mapper.to_entity(media)
        merged = await self.db.merge(entity)
        await self.db.flush()
        persisted = self._mapper.to_domain(merged)
        return self._mapper.merge_transient_data(persisted, media)

    async def update(self, media: MediaAggregate) -> MediaAggregate:
        return await self.save(media)

    async def delete(self, media_id: UUID) -> None:
        result = await self.db.execute(select(MediaEntity).where(MediaEntity.id == media_id))
        entity = result.scalar_one_or_none()
        if entity is not None:
            await self.db.delete(entity)
            await self.db.flush()

    async def update_status(
        self,
        media_id: UUID,
        status: MediaStatus,
        *,
        error_message: Optional[str] = None,
    ) -> MediaAggregate:
        result = await self.db.execute(select(MediaEntity).where(MediaEntity.id == media_id))
        entity = result.scalar_one()
        previous_status = entity.status
        previous_error = entity.error_message
        entity.status = status
        entity.error_message = error_message
        await self.db.flush()
        aggregate = self._mapper.to_domain(entity)
        updated = aggregate.update(error_message=error_message)

        # Notify user when status actually changes or when we have a new error
        should_notify = previous_status != status or (error_message and error_message != previous_error)
        if should_notify:
            try:
                enqueue_media_status_notification(
                    user_id=entity.user_id,
                    media_id=entity.id,
                    status=status,
                    error_message=error_message,
                )
            except Exception as exc:  # pragma: no cover - defensive guard
                logger.warning(
                    "media.notifications.enqueue_failed",
                    media_id=str(entity.id),
                    user_id=str(entity.user_id),
                    status=status.value if isinstance(status, MediaStatus) else str(status),
                    error=str(exc),
                )

        return updated

    async def list_paginated(
        self,
        *,
        page: int = 1,
        limit: int = 10,
        user_id: Optional[UUID] = None,
        status: Optional[MediaStatus] = None,
        search: Optional[str] = None,
    ) -> List[MediaAggregate]:
        stmt = select(MediaEntity)
        if user_id is not None:
            stmt = stmt.where(MediaEntity.user_id == user_id)
        if status is not None:
            stmt = stmt.where(MediaEntity.status == status)
        if search:
            stmt = stmt.where(MediaEntity.original_file_path.ilike(f"%{search}%"))

        offset = max(page - 1, 0) * limit
        stmt = stmt.order_by(MediaEntity.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(stmt)
        return [self._mapper.to_domain(entity) for entity in result.scalars().all()]

    async def list_all(
        self,
        user_id: Optional[UUID] = None,
        status: Optional[MediaStatus] = None,
    ) -> List[MediaAggregate]:
        return await self.list_paginated(page=1, limit=10_000, user_id=user_id, status=status)

    async def count_all(self) -> int:
        result = await self.db.execute(select(func.count()).select_from(MediaEntity))
        return result.scalar_one()

    async def count_by_status(self, status: MediaStatus) -> int:
        stmt = select(func.count()).select_from(MediaEntity).where(MediaEntity.status == status)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def count_by_user(self, user_id: UUID) -> int:
        stmt = select(func.count()).select_from(MediaEntity).where(MediaEntity.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def count_by_user_and_status(self, user_id: UUID, status: MediaStatus) -> int:
        stmt = (
            select(func.count())
            .select_from(MediaEntity)
            .where(MediaEntity.user_id == user_id)
            .where(MediaEntity.status == status)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()
