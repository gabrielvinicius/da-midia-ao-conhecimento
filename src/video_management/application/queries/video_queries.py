"""Compatibility query services for legacy video management module."""

from __future__ import annotations

from typing import Any, List
from uuid import UUID

from src.video_management.domain.video import Video


class VideoQueries:
    def __init__(self, video_repository: Any) -> None:
        self._video_repository = video_repository

    async def get_video_by_id(self, video_id: str) -> Video | None:
        return await self._video_repository.find_by_id(UUID(str(video_id)))

    async def list_user_videos(self, *, user_id: str, skip: int = 0, limit: int = 10) -> List[Video]:
        return await self._video_repository.list_by_user(user_id=UUID(str(user_id)), skip=skip, limit=limit)


__all__ = ["VideoQueries"]
