from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from src.user_management.domain.user import User
from src.user_management.infrastructure.user_repository import UserRepository


class AuthQueries:
    """Query-only accessors for authentication module."""

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def get_by_id(self, user_id: str | UUID) -> Optional[User]:
        """Backward-compatible helper preserved for legacy tests/routes."""
        if not isinstance(user_id, UUID):
            user_id = UUID(str(user_id))
        return await self.get_user_by_id(user_id)

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        return await self.user_repository.find_by_id(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        return await self.user_repository.find_by_email(email)

    async def list_all(self, *, page: int = 1, limit: int = 50, search: Optional[str] = None) -> List[User]:
        # For compatibility we just delegate to repository list_all; pagination/search can be added later.
        users = await self.user_repository.list_all()
        if search:
            lowered = search.lower()
            users = [user for user in users if lowered in user.email.lower()]
        start = (page - 1) * limit
        end = start + limit
        return users[start:end]
