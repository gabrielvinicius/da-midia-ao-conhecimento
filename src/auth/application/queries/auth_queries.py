"""Query services that expose read-only access to auth data."""

from typing import List, Optional, Union
from uuid import UUID

from src.auth.domain.user import User
from src.auth.infrastructure.user_repository import UserRepository


class AuthQueries:
    """Provides read-side operations for the authentication domain."""

    def __init__(self, user_repository: UserRepository) -> None:
        self._user_repository = user_repository

    async def get_by_id(self, user_id: Union[UUID, str]) -> Optional[User]:
        """Return a user by its identifier."""

        if isinstance(user_id, str):
            user_id = UUID(user_id)
        return await self._user_repository.find_by_id(user_id)

    async def get_by_email(self, email: str) -> Optional[User]:
        """Return a user by e-mail address."""

        return await self._user_repository.find_by_email(email)

    async def list_all(
        self,
        page: int = 1,
        limit: int = 10,
        search: Optional[str] = None,
    ) -> List[User]:
        """Return a paginated list of users."""

        return await self._user_repository.list_all(page=page, limit=limit, search=search)

    async def count_all(self) -> int:
        """Return the total number of users."""

        return await self._user_repository.count_all()

    async def count_active(self) -> int:
        """Return the total number of active users."""

        return await self._user_repository.count_active()
