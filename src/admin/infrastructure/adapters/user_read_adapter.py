from __future__ import annotations

from src.admin.application.ports import AdminUserReadPort
from src.user_management.application.auth_queries import UserReadService
from src.user_management.application.dtos import GetUserQuery


class UserReadAdapter(AdminUserReadPort):
    """Adapter exposing only read operations over users to the admin façade (CQRS read side)."""

    def __init__(self, auth_queries: UserReadService) -> None:
        self._svc = auth_queries

    async def count_all(self) -> int:
        return await self._svc.count_all()

    async def count_active(self) -> int:
        return await self._svc.count_active()

    async def get_user_by_id(self, query: GetUserQuery):
        return await self._svc.get_user_by_id(query)


__all__ = ["UserReadAdapter"]
