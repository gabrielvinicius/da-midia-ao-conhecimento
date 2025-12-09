from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from src.user_management.domain.user import User
from src.user_management.infrastructure.repositories.sqlalchemy_user_repository import UserRepository
from src.user_management.application.queries.dto import GetUserQuery, ListUsersQuery


class AuthQueries:
    """Query-only accessors for authentication module."""

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def get_user_by_id(self, query: GetUserQuery) -> Optional[User]:
        return await self.user_repository.find_by_id(query.user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        return await self.user_repository.find_by_email(email)

    async def list_all(self, query: ListUsersQuery) -> List[User]:
        return await self.user_repository.list_all(page=query.page, limit=query.limit, search=query.search)

    async def count_all(self) -> int:
        return await self.user_repository.count_all()

    async def count_active(self) -> int:
        return await self.user_repository.count_active()

    async def count_filtered(self, *, search: Optional[str] = None) -> int:
        return await self.user_repository.count_filtered(search=search)