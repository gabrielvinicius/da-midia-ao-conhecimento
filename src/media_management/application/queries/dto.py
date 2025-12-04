from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.shared.domain.enums import MediaStatus


@dataclass(frozen=True)
class GetMediaQuery:
    media_id: UUID


@dataclass(frozen=True)
class ListMediaQuery:
    page: int = 1
    limit: int = 10
    user_id: Optional[UUID] = None
    status: Optional[MediaStatus] = None
    search: Optional[str] = None


@dataclass(frozen=True)
class GetMediaStatisticsQuery:
    user_id: Optional[UUID] = None
