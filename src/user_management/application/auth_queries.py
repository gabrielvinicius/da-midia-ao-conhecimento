from __future__ import annotations

from uuid import UUID

from src.user_management.application.ports import UserQueriesPort, UserRepositoryPort


class UserReadService(UserQueriesPort):
    """Serviço de leitura para autenticação/usuário usando apenas o repositório via port."""

    def __init__(self, user_repository: UserRepositoryPort) -> None:
        self.user_repository = user_repository

    async def get_user_by_email(self, email: str):
        return await self.user_repository.find_by_email(email)

    async def get_user_by_id(self, user_id: UUID):
        return await self.user_repository.find_by_id(user_id)

    async def list_all(
        self,
        *,
        page: int = 1,
        limit: int = 10,
        search: str | None = None,
    ):
        return await self.user_repository.list_all(page=page, limit=limit, search=search)

    async def count_all(self) -> int:
        return await self.user_repository.count_all()

    async def count_active(self) -> int:
        return await self.user_repository.count_active()

    async def count_filtered(self, search: str | None = None) -> int:
        return await self.user_repository.count_filtered(search=search)


__all__ = ["UserReadService"]
