from __future__ import annotations

from typing import Optional
from uuid import UUID

from src.user_management.application.ports import UserRepositoryPort
from src.user_management.domain import User
from src.user_management.infrastructure.repositories.sqlalchemy_user_repository import (
    UserRepository,
)


class UserRepositoryAdapter(UserRepositoryPort):
    def __init__(self, repo: UserRepository):
        self._repo = repo

    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        return await self._repo.find_by_id(user_id)

    async def find_by_email(self, email: str) -> Optional[User]:
        return await self._repo.find_by_email(email)

    async def list_all(
        self, *, page: int, limit: int, search: Optional[str]
    ) -> list[User]:
        return await self._repo.list_all(page=page, limit=limit, search=search)

    async def count_all(self) -> int:
        return await self._repo.count_all()

    async def count_active(self) -> int:
        return await self._repo.count_active()

    async def count_filtered(self, *, search: Optional[str]) -> int:
        return await self._repo.count_filtered(search=search)

    async def save(self, user: User) -> User:
        return await self._repo.save(user)

    async def delete(self, user_id: UUID) -> bool:
        return await self._repo.delete(user_id)


__all__ = ["UserRepositoryAdapter"]
