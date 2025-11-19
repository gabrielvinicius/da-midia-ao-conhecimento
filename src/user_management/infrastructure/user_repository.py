# src/user_management/infrastructure/user_repository.py
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management.domain.user import User


class UserRepository:
    def __init__(self, db):
        self.db = db

    async def save(self, user: User) -> User:
        from sqlalchemy.ext.asyncio import AsyncSession
        if isinstance(self.db, AsyncSession):
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            return user
        else:  # It's a sync session
            return self.save_sync(user)

    def save_sync(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        from sqlalchemy.ext.asyncio import AsyncSession
        if isinstance(self.db, AsyncSession):
            return await self.db.get(User, user_id)
        else:  # It's a sync session
            return self.find_by_id_sync(user_id)

    def find_by_id_sync(self, user_id: UUID) -> Optional[User]:
        from sqlalchemy import select
        stmt = select(User).where(User.id == user_id)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_email(self, email: str) -> Optional[User]:
        from sqlalchemy.ext.asyncio import AsyncSession
        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(select(User).where(User.email == email))
            return result.scalar_one_or_none()
        else:  # It's a sync session
            return self.find_by_email_sync(email)

    def find_by_email_sync(self, email: str) -> Optional[User]:
        from sqlalchemy import select
        stmt = select(User).where(User.email == email)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(self, page: int = 1, limit: int = 10, search: Optional[str] = None) -> List[User]:
        """Lists all users with pagination and search."""
        from sqlalchemy.ext.asyncio import AsyncSession
        if isinstance(self.db, AsyncSession):
            query = select(User)
            if search:
                query = query.where(User.email.ilike(f"%{search}%"))

            offset = (page - 1) * limit
            query = query.offset(offset).limit(limit)

            result = await self.db.execute(query)
            return result.scalars().all()
        else:  # It's a sync session
            return self.list_all_sync(page, limit, search)

    def list_all_sync(self, page: int = 1, limit: int = 10, search: Optional[str] = None) -> List[User]:
        """Lists all users with pagination and search."""
        from sqlalchemy import select
        query = select(User)
        if search:
            query = query.where(User.email.ilike(f"%{search}%"))

        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = self.db.execute(query)
        return result.scalars().all()

    async def count_all(self) -> int:
        """Return the total number of users."""
        from sqlalchemy.ext.asyncio import AsyncSession
        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(select(func.count()).select_from(User))
            return result.scalar_one()
        else:  # It's a sync session
            return self.count_all_sync()

    def count_all_sync(self) -> int:
        """Return the total number of users."""
        from sqlalchemy import select
        result = self.db.execute(select(func.count()).select_from(User))
        return result.scalar_one()

    async def count_filtered(self, search: Optional[str] = None) -> int:
        from sqlalchemy.ext.asyncio import AsyncSession
        if isinstance(self.db, AsyncSession):
            stmt = select(func.count()).select_from(User)
            if search:
                stmt = stmt.where(User.email.ilike(f"%{search}%"))
            result = await self.db.execute(stmt)
            return result.scalar_one()
        return self.count_filtered_sync(search=search)

    def count_filtered_sync(self, search: Optional[str] = None) -> int:
        from sqlalchemy import select
        stmt = select(func.count()).select_from(User)
        if search:
            stmt = stmt.where(User.email.ilike(f"%{search}%"))
        result = self.db.execute(stmt)
        return result.scalar_one()

    async def count_active(self) -> int:
        """Return the total number of active users."""
        from sqlalchemy.ext.asyncio import AsyncSession
        if isinstance(self.db, AsyncSession):
            stmt = select(func.count()).select_from(User).where(User.is_active.is_(True))
            result = await self.db.execute(stmt)
            return result.scalar_one()
        else:  # It's a sync session
            return self.count_active_sync()

    def count_active_sync(self) -> int:
        """Return the total number of active users."""
        from sqlalchemy import select
        stmt = select(func.count()).select_from(User).where(User.is_active.is_(True))
        result = self.db.execute(stmt)
        return result.scalar_one()

    async def delete(self, user_id: UUID) -> bool:
        from sqlalchemy.ext.asyncio import AsyncSession
        if isinstance(self.db, AsyncSession):
            user = await self.find_by_id(user_id)
            if user:
                await self.db.delete(user)
                await self.db.commit()
                return True
            return False
        else:  # It's a sync session
            return self.delete_sync(user_id)

    def delete_sync(self, user_id: UUID) -> bool:
        user = self.find_by_id_sync(user_id)
        if user:
            self.db.delete(user)
            self.db.commit()
            return True
        return False
