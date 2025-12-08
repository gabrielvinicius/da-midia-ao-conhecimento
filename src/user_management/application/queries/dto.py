from dataclasses import dataclass
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class GetUserQuery:
    user_id: UUID


@dataclass(frozen=True)
class ListUsersQuery:
    page: int = 1
    limit: int = 50
    search: Optional[str] = None
