# src/auth/application/queries/auth_queries.py
import math
from typing import Optional
from uuid import UUID

from src.auth.domain.user import User
from src.auth.infrastructure.user_repository import UserRepository
from src.shared.api.schemas import PaginatedResponse


class AuthQueries:
    """Handles all read-only operations for users."""
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Retrieves a user by their unique ID."""
        return await self.user_repository.find_by_id(UUID(user_id))

    async def list_all(self, page: int, limit: int, search: Optional[str]) -> PaginatedResponse[User]:
        """Lists all users with pagination and search."""
        items, total_items = await self.user_repository.list_all(page=page, limit=limit, search=search)
        
        total_pages = math.ceil(total_items / limit) if total_items > 0 else 1

        return PaginatedResponse(
            total_items=total_items,
            total_pages=total_pages,
            current_page=page,
            items=items
        )
