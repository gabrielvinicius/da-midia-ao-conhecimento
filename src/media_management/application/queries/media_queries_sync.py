"""Synchronous counterpart of MediaQueries for Celery contexts."""
from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from src.media_management.domain.enums import MediaStatus
from src.media_management.domain.media import Media
from src.media_management.infrastructure.media_repository_sync import (
    MediaRepositorySync,
)


class MediaQueriesSync:
    def __init__(self, media_repository: MediaRepositorySync):
        self.media_repository = media_repository

    def get_by_id(self, media_id: UUID) -> Optional[Media]:
        return self.media_repository.get_by_id(media_id)

    def list_all(
        self,
        page: int = 1,
        limit: int = 10,
        user_id: Optional[UUID] = None,
        status: Optional[MediaStatus] = None,
        search: Optional[str] = None,
    ) -> List[Media]:
        return self.media_repository.list_paginated(
            page=page,
            limit=limit,
            user_id=user_id,
            status=status,
            search=search,
        )

    def count_all(self) -> int:
        return self.media_repository.count_all()

    def count_by_status(self, status: MediaStatus) -> int:
        return self.media_repository.count_by_status(status)

    def count_filtered(
        self,
        *,
        user_id: Optional[UUID] = None,
        status: Optional[MediaStatus] = None,
        search: Optional[str] = None,
    ) -> int:
        return self.media_repository.count_filtered(
            user_id=user_id,
            status=status,
            search=search,
        )

    def count_by_user(self, user_id: UUID) -> int:
        return self.media_repository.count_by_user(user_id)

    def count_by_user_and_status(self, user_id: UUID, status: MediaStatus) -> int:
        return self.media_repository.count_by_user_and_status(user_id, status)


__all__ = ["MediaQueriesSync"]
