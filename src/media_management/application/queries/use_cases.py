from typing import List, Dict, Any, Optional
from uuid import UUID

from src.media_management.domain.media import Media
from src.media_management.infrastructure.repositories import MediaRepository
from src.shared.domain.enums import MediaStatus
from .dto import GetMediaQuery, ListMediaQuery, GetMediaStatisticsQuery


class GetMedia:
    def __init__(self, repository: MediaRepository):
        self.repository = repository

    async def execute(self, query: GetMediaQuery) -> Optional[Media]:
        return await self.repository.get_by_id(query.media_id)


class ListMedia:
    def __init__(self, repository: MediaRepository):
        self.repository = repository

    async def execute(self, query: ListMediaQuery) -> List[Media]:
        return await self.repository.list_paginated(
            page=query.page,
            limit=query.limit,
            user_id=query.user_id,
            status=query.status,
            search=query.search,
        )


class GetMediaStatistics:
    def __init__(self, repository: MediaRepository):
        self.repository = repository

    async def execute(self, query: GetMediaStatisticsQuery) -> Dict[str, Any]:
        if query.user_id:
            total = await self.repository.count_by_user(query.user_id)
            by_status = {}
            for status in MediaStatus:
                count = await self.repository.count_by_user_and_status(query.user_id, status)
                by_status[status.value] = count
        else:
            total = await self.repository.count_all()
            by_status = {}
            for status in MediaStatus:
                count = await self.repository.count_by_status(status)
                by_status[status.value] = count

        return {"total": total, "by_status": by_status}
