from uuid import UUID
from typing import Optional, Sequence, Union, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, func, delete
from src.auth.domain.user import User
import logging

logger = logging.getLogger(__name__)

class UserRepository:
    def __init__(self, db: Union[AsyncSession, Session]):
        self.db = db

    def _is_async(self):
        return isinstance(self.db, AsyncSession)

    async def save(self, user: User) -> User:
        self.db.add(user)
        try:
            if self._is_async():
                await self.db.commit()
                await self.db.refresh(user)
            else:
                self.db.commit()
                self.db.refresh(user)
            return user
        except Exception as e:
            if self._is_is_async():
                await self.db.rollback()
            else:
                self.db.rollback()
            logger.error(f"Error saving user {getattr(user, 'id', None)}: {e}")
            raise

    async def find_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        if self._is_async():
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        else:
            result = self.db.execute(stmt)
            return result.scalar_one_or_none()

    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        if self._is_async():
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        else:
            result = self.db.execute(stmt)
            return result.scalar_one_or_none()

    async def delete(self, user_id: UUID) -> bool:
        stmt = delete(User).where(User.id == user_id).returning(User.id)
        try:
            if self._is_async():
                result = await self.db.execute(stmt)
                await self.db.commit()
                deleted_id = result.scalar()
            else:
                result = self.db.execute(stmt)
                self.db.commit()
                deleted_id = result.scalar()
            return deleted_id is not None
        except Exception as e:
            if self._is_async():
                await self.db.rollback()
            else:
                self.db.rollback()
            logger.error(f"Error deleting user {user_id}: {e}")
            raise

    async def list_all(self, page: int, limit: int, search: Optional[str] = None) -> Tuple[Sequence[User], int]:
        """Returns a paginated and searchable list of all users."""
        if not self._is_async():
            raise NotImplementedError("Pagination is only supported in async mode.")

        # Base query
        stmt = select(User)
        if search:
            stmt = stmt.where(User.email.ilike(f"%{search}%"))

        # Get total count for pagination metadata
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_items_result = await self.db.execute(count_stmt)
        total_items = total_items_result.scalar_one()

        # Get paginated items
        paginated_stmt = stmt.offset((page - 1) * limit).limit(limit).order_by(User.created_at.desc())
        items_result = await self.db.execute(paginated_stmt)
        items = items_result.scalars().all()

        return items, total_items

    async def count_all(self) -> int:
        """Returns the total count of all users."""
        if not self._is_async():
            raise NotImplementedError("Count all is only supported in async mode.")
        
        stmt = select(func.count()).select_from(User)
        result = await self.db.execute(stmt)
        return result.scalar_one()
