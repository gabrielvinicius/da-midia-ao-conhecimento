# src/auth/infrastructure/user_repository.py
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management.domain.user import User


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save(self, user: User) -> User:
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        return await self.db.get(User, user_id)

    async def find_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def list_all(self, page: int = 1, limit: int = 10, search: Optional[str] = None) -> List[User]:
        """Lists all users with pagination and search."""
        query = select(User)
        if search:
            query = query.where(User.email.ilike(f"%{search}%"))

        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def count_all(self) -> int:
        """Return the total number of users."""

        result = await self.db.execute(select(func.count()).select_from(User))
        return result.scalar_one()

    async def count_active(self) -> int:
        """Return the total number of active users."""

        stmt = select(func.count()).select_from(User).where(User.is_active.is_(True))
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def delete(self, user_id: UUID) -> bool:
        user = await self.find_by_id(user_id)
        if user:
            await self.db.delete(user)
            await self.db.commit()
            return True
        return False
