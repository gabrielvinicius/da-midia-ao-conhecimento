"""Repositório de usuários (SQLAlchemy, sessão assíncrona)."""
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select

from src.user_management.domain.entities.user import User
from src.user_management.infrastructure.persistence.models import UserModel
from src.shared.infrastructure.database.unit_of_work import commit as uow_commit


class UserRepository:
    def __init__(self, db):
        self.db = db

    async def save(self, user: User) -> User:
        """Insere ou atualiza.

        merge, e não add: o modelo criado a partir da entidade é um objeto novo,
        e add tentaria inseri-lo de novo, violando a chave primária, sempre que
        um usuário existente fosse alterado (troca de senha, perfil, ativação).
        """
        model = await self.db.merge(UserModel.from_domain(user))
        await uow_commit(self.db)
        return model.to_domain()

    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        model = await self.db.get(UserModel, user_id)
        return model.to_domain() if model else None

    async def find_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(UserModel).where(UserModel.email == email))
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def list_all(
        self,
        *,
        page: int = 1,
        limit: int = 10,
        search: Optional[str] = None,
    ) -> list[User]:
        """Lists all users with pagination and search."""
        query = select(UserModel)
        if search:
            query = query.where(UserModel.email.ilike(f"%{search}%"))
        query = query.offset((page - 1) * limit).limit(limit)
        result = await self.db.execute(query)
        return [model.to_domain() for model in result.scalars().all()]

    async def count_all(self) -> int:
        """Return the total number of users."""
        result = await self.db.execute(select(func.count()).select_from(UserModel))
        return result.scalar_one()

    async def count_filtered(self, search: Optional[str] = None) -> int:
        stmt = select(func.count()).select_from(UserModel)
        if search:
            stmt = stmt.where(UserModel.email.ilike(f"%{search}%"))
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def count_active(self) -> int:
        """Return the total number of active users."""
        stmt = select(func.count()).select_from(UserModel).where(UserModel.is_active.is_(True))
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def delete(self, user_id: UUID) -> bool:
        model = await self.db.get(UserModel, user_id)
        if not model:
            return False
        await self.db.delete(model)
        await uow_commit(self.db)
        return True
