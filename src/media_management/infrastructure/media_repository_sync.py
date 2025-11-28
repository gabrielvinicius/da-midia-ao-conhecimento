"""Synchronous SQLAlchemy repository for Celery/job-runner contexts."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.media_management.application.notifications import enqueue_media_status_notification
from src.media_management.domain.enums import MediaStatus
from src.media_management.domain.media_state import DEFAULT_MEDIA_STATE_MACHINE
from src.media_management.domain.model import MediaAggregate
from src.media_management.infrastructure.orm.media_entity import MediaEntity
from src.media_management.infrastructure.orm.media_mapper import MediaMapper


class MediaRepositorySync:
    """Sync variant of the media repository used inside Celery workers."""

    def __init__(self, db: Session, mapper: Optional[MediaMapper] = None) -> None:
        self.db = db
        self._mapper = mapper or MediaMapper()

    # --- Persistence helpers -------------------------------------------------
    def get_by_id(self, media_id: UUID) -> Optional[MediaAggregate]:
        stmt = select(MediaEntity).where(MediaEntity.id == media_id)
        entity = self.db.execute(stmt).scalar_one_or_none()
        if entity is None:
            return None
        return self._mapper.to_domain(entity)

    def update_status(
        self,
        media_id: UUID,
        status: MediaStatus,
        *,
        error_message: Optional[str] = None,
        force_notify: bool = False,
    ) -> Optional[MediaAggregate]:
        stmt = select(MediaEntity).where(MediaEntity.id == media_id)
        entity = self.db.execute(stmt).scalar_one_or_none()
        if entity is None:
            return None

        previous_status = entity.status
        DEFAULT_MEDIA_STATE_MACHINE.assert_transition(previous_status, status)
        previous_error = entity.error_message
        entity.status = status
        entity.error_message = error_message
        self.db.flush()

        aggregate = self._mapper.to_domain(entity)
        updated = aggregate.update(error_message=error_message)

        should_notify = force_notify or previous_status != status or (
            error_message and error_message != previous_error
        )
        if should_notify:
            enqueue_media_status_notification(
                user_id=entity.user_id,
                media_id=entity.id,
                status=status,
                error_message=error_message,
            )

        return updated

    # --- Query helpers -------------------------------------------------------
    def list_paginated(
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
        result = self.db.execute(stmt)
        return [self._mapper.to_domain(entity) for entity in result.scalars().all()]

    def count_filtered(
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
        return self.db.execute(stmt).scalar_one()

    def count_all(self) -> int:
        stmt = select(func.count()).select_from(MediaEntity)
        return self.db.execute(stmt).scalar_one()

    def count_by_status(self, status: MediaStatus) -> int:
        stmt = select(func.count()).select_from(MediaEntity).where(MediaEntity.status == status)
        return self.db.execute(stmt).scalar_one()

    def count_by_user(self, user_id: UUID) -> int:
        stmt = select(func.count()).select_from(MediaEntity).where(MediaEntity.user_id == user_id)
        return self.db.execute(stmt).scalar_one()

    def count_by_user_and_status(self, user_id: UUID, status: MediaStatus) -> int:
        stmt = (
            select(func.count())
            .select_from(MediaEntity)
            .where(MediaEntity.user_id == user_id)
            .where(MediaEntity.status == status)
        )
        return self.db.execute(stmt).scalar_one()


__all__ = ["MediaRepositorySync"]
