from __future__ import annotations

from typing import Optional
from uuid import UUID

from src.notifications.application.ports import AuthQueriesPort
from src.user_management.infrastructure.repositories.sqlalchemy_user_repository import (
    UserRepository,
)


class NotificationsAuthQueriesAdapter(AuthQueriesPort):
    """Adapter de leitura de usuário para o bounded context `notifications`."""

    def __init__(self, *, db_session) -> None:
        self._repo = UserRepository(db=db_session)

    async def get_user_by_id(self, user_id):
        return await self._repo.find_by_id(UUID(str(user_id)))

    async def get_user_by_email(self, email: str):
        return await self._repo.find_by_email(email)

    async def list_all(self, page: int, limit: int, search: Optional[str] = None):
        return await self._repo.list_all(page=page, limit=limit, search=search)

    async def count_filtered(self, search: Optional[str] = None) -> int:
        return await self._repo.count_filtered(search=search)


__all__ = ["NotificationsAuthQueriesAdapter"]

