from __future__ import annotations

from src.notifications.application.ports import AuthQueriesPort
from src.user_management.application.auth_queries import UserReadService


class AuthQueriesAdapter(AuthQueriesPort):
    """Adapter exposing UserReadService as the AuthQueriesPort for notifications."""

    def __init__(self, user_read_service: UserReadService) -> None:
        self._svc = user_read_service

    async def get_user_by_email(self, email: str):
        return await self._svc.get_user_by_email(email)

    async def get_user_by_id(self, user_id):
        return await self._svc.get_user_by_id(user_id)

    async def list_all(self):
        return await self._svc.list_all()

    async def count_all(self) -> int:
        return await self._svc.count_all()

    async def count_active(self) -> int:
        return await self._svc.count_active()


__all__ = ["AuthQueriesAdapter"]
