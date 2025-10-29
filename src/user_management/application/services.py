from __future__ import annotations

from typing import Optional
from uuid import UUID

from src.auth.domain.user import User, UserRole
from src.auth.infrastructure.user_repository import UserRepository
from src.shared.utils.id_generator import generate_id
from src.shared.utils.password_utils import hash_password


class UserService:
    """Unified user service (create, fetch)."""

    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    async def create_user(self, email: str, password: str, role: str = "user") -> User:
        # Minimal validation; full validation exists in existing AuthService
        if not email or "@" not in email:
            raise ValueError("Invalid email format")
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        password_hash = hash_password(password)
        user = User(
            id=generate_id(),
            email=email,
            password_hash=password_hash,
            role=UserRole(role),
        )
        return await self.user_repository.save(user)

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        return await self.user_repository.find_by_id(user_id)

    # Backwards-compatible API used by auth router
    async def register_user(self, email: str, password: str) -> dict[str, object]:
        user = await self.create_user(email=email, password=password, role="user")
        return {
            "success": True,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role.value,
            },
        }
