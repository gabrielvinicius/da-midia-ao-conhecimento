"""In-memory repository used for lightweight/tests to avoid DB dependencies."""
from __future__ import annotations

from typing import Optional
from uuid import UUID, uuid4

from src.user_management.domain.entities.user import User


class FakeUserRepository:
    def __init__(self) -> None:
        self._users: dict[UUID, User] = {}

    async def save(self, user: User) -> User:
        if user.id is None:
            user.id = uuid4()
        self._users[user.id] = user
        return user

    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        return self._users.get(user_id)

    async def get_user_by_id(self, user_id):
        return await self.find_by_id(user_id)

    async def find_by_email(self, email: str) -> Optional[User]:
        for u in self._users.values():
            if u.email == email:
                return u
        return None

    async def get_user_by_email(self, email: str) -> Optional[User]:
        return await self.find_by_email(email)

    async def list_all(
        self, *, page: int = 1, limit: int = 10, search: str | None = None
    ) -> list[User]:
        users = list(self._users.values())
        if search:
            users = [u for u in users if search.lower() in u.email.lower()]
        start = (page - 1) * limit
        end = start + limit
        return users[start:end]

    async def count_all(self) -> int:
        return len(self._users)

    async def count_active(self) -> int:
        return sum(1 for u in self._users.values() if u.is_active)

    async def count_filtered(self, *, search: Optional[str]) -> int:
        if not search:
            return len(self._users)
        return sum(1 for u in self._users.values() if search.lower() in u.email.lower())

    async def delete(self, user_id: UUID) -> bool:
        return self._users.pop(user_id, None) is not None


__all__ = ["FakeUserRepository"]
