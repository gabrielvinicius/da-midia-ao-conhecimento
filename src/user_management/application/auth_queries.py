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

    async def list_users(self, query) -> dict:
        """Página de usuários para a administração.

        A rota /admin/users chamava este método, que não existia: a página de
        gestão de usuários respondia com erro 500.
        """
        users = await self.list_all(page=query.page, limit=query.limit, search=query.search)
        total = await self.count_filtered(search=query.search)
        return {
            "items": [
                {
                    "id": u.id,
                    "email": u.email,
                    "is_active": u.is_active,
                    "role": getattr(u.role, "value", u.role),
                }
                for u in users
            ],
            "total_items": total,
            "current_page": query.page,
            "total_pages": max(1, -(-total // query.limit)),
        }


__all__ = ["UserReadService"]
