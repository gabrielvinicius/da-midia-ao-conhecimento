# src/user_management/infrastructure/user_repository.py
from typing import List, Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management.domain.user import User
from src.user_management.infrastructure.user_model import UserModel


class UserRepository:
    def __init__(self, db):
        self.db = db

    async def save(self, user: User) -> User:
        model = UserModel.from_domain(user)
        from sqlalchemy.ext.asyncio import AsyncSession
        
        if isinstance(self.db, AsyncSession):
            self.db.add(model)
            await self.db.commit()
            await self.db.refresh(model)
            return model.to_domain()
        else:  # It's a sync session
            return self.save_sync(user)

    def save_sync(self, user: User) -> User:
        model = UserModel.from_domain(user)
        # Check if user exists to update instead of insert if needed, 
        # but typically 'add' handles it if attached to session properly.
        # However, converting from domain creates a detached object.
        # We might need to merge.
        merged_model = self.db.merge(model)
        self.db.commit()
        self.db.refresh(merged_model)
        return merged_model.to_domain()

    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        from sqlalchemy.ext.asyncio import AsyncSession
        if isinstance(self.db, AsyncSession):
            model = await self.db.get(UserModel, user_id)
            return model.to_domain() if model else None
        else:  # It's a sync session
            return self.find_by_id_sync(user_id)

    def find_by_id_sync(self, user_id: UUID) -> Optional[User]:
        from sqlalchemy import select
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = self.db.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def find_by_email(self, email: str) -> Optional[User]:
        from sqlalchemy.ext.asyncio import AsyncSession
        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(select(UserModel).where(UserModel.email == email))
            model = result.scalar_one_or_none()
            return model.to_domain() if model else None
        else:  # It's a sync session
            return self.find_by_email_sync(email)

    def find_by_email_sync(self, email: str) -> Optional[User]:
        from sqlalchemy import select
        stmt = select(UserModel).where(UserModel.email == email)
        result = self.db.execute(stmt)
        model = result.scalar_one_or_none()
        return model.to_domain() if model else None

    async def list_all(self, page: int = 1, limit: int = 10, search: Optional[str] = None) -> List[User]:
        """Lists all users with pagination and search."""
        from sqlalchemy.ext.asyncio import AsyncSession
        if isinstance(self.db, AsyncSession):
            query = select(UserModel)
            if search:
                query = query.where(UserModel.email.ilike(f"%{search}%"))

            offset = (page - 1) * limit
            query = query.offset(offset).limit(limit)

            result = await self.db.execute(query)
            return [model.to_domain() for model in result.scalars().all()]
        else:  # It's a sync session
            return self.list_all_sync(page, limit, search)

    def list_all_sync(self, page: int = 1, limit: int = 10, search: Optional[str] = None) -> List[User]:
        """Lists all users with pagination and search."""
        from sqlalchemy import select
        query = select(UserModel)
        if search:
            query = query.where(UserModel.email.ilike(f"%{search}%"))

        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        result = self.db.execute(query)
        return [model.to_domain() for model in result.scalars().all()]

    async def count_all(self) -> int:
        """Return the total number of users."""
        from sqlalchemy.ext.asyncio import AsyncSession
        if isinstance(self.db, AsyncSession):
            result = await self.db.execute(select(func.count()).select_from(UserModel))
            return result.scalar_one()
        else:  # It's a sync session
            return self.count_all_sync()

    def count_all_sync(self) -> int:
        """Return the total number of users."""
        from sqlalchemy import select
        result = self.db.execute(select(func.count()).select_from(UserModel))
        return result.scalar_one()

    async def count_filtered(self, search: Optional[str] = None) -> int:
        from sqlalchemy.ext.asyncio import AsyncSession
        if isinstance(self.db, AsyncSession):
            stmt = select(func.count()).select_from(UserModel)
            if search:
                stmt = stmt.where(UserModel.email.ilike(f"%{search}%"))
            result = await self.db.execute(stmt)
            return result.scalar_one()
        return self.count_filtered_sync(search=search)

    def count_filtered_sync(self, search: Optional[str] = None) -> int:
        from sqlalchemy import select
        stmt = select(func.count()).select_from(UserModel)
        if search:
            stmt = stmt.where(UserModel.email.ilike(f"%{search}%"))
        result = self.db.execute(stmt)
        return result.scalar_one()

    async def count_active(self) -> int:
        """Return the total number of active users."""
        from sqlalchemy.ext.asyncio import AsyncSession
        if isinstance(self.db, AsyncSession):
            stmt = select(func.count()).select_from(UserModel).where(UserModel.is_active.is_(True))
            result = await self.db.execute(stmt)
            return result.scalar_one()
        else:  # It's a sync session
            return self.count_active_sync()

    def count_active_sync(self) -> int:
        """Return the total number of active users."""
        from sqlalchemy import select
        stmt = select(func.count()).select_from(UserModel).where(UserModel.is_active.is_(True))
        result = self.db.execute(stmt)
        return result.scalar_one()

    async def delete(self, user_id: UUID) -> bool:
        from sqlalchemy.ext.asyncio import AsyncSession
        if isinstance(self.db, AsyncSession):
            model = await self.db.get(UserModel, user_id)
            if model:
                await self.db.delete(model)
                await self.db.commit()
                return True
            return False
        else:  # It's a sync session
            return self.delete_sync(user_id)

    def delete_sync(self, user_id: UUID) -> bool:
        # Use find_by_id_sync to get the model, but wait, find_by_id_sync returns Domain User!
        # We need to fetch the MODEL to delete it.
        from sqlalchemy import select
        stmt = select(UserModel).where(UserModel.id == user_id)
        result = self.db.execute(stmt)
        model = result.scalar_one_or_none()
        
        if model:
            self.db.delete(model)
            self.db.commit()
            return True
        return False