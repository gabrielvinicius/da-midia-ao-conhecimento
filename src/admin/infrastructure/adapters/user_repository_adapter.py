from __future__ import annotations

from src.admin.application.ports import AdminUserRepositoryPort
from src.user_management.infrastructure.repositories.sqlalchemy_user_repository import (
    UserRepository,
)


class UserRepositoryAdapter(AdminUserRepositoryPort):
    def __init__(self, repo: UserRepository):
        self._repo = repo

    async def find_by_id(self, user_id):
        return await self._repo.find_by_id(user_id)

    async def save(self, user):
        return await self._repo.save(user)

    async def delete(self, user_id):
        return await self._repo.delete(user_id)


__all__ = ["UserRepositoryAdapter"]
