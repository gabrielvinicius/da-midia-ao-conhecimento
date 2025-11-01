from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from src.user_management.domain.user import User, UserRole
from src.user_management.infrastructure.user_repository import UserRepository
from src.user_management.config.settings import AuthSettings
from src.user_management.utils.token import create_access_token
from src.shared.utils.id_generator import generate_id
from src.shared.utils.password_utils import hash_password, verify_password


class UserService:
    """Unified user service (create, fetch)."""

    def __init__(self, user_repository: UserRepository, settings: Optional[AuthSettings] = None) -> None:
        self.user_repository = user_repository
        self.settings = settings or AuthSettings()

    async def create_user(self, email: str, password: str, role: str = "user") -> User:
        self._validate_email_format(email)
        await self._ensure_email_available(email)
        self._validate_password_strength(password)
        normalised_role = self._normalise_role(role)

        user = User(
            id=generate_id(),
            email=email,
            password_hash=hash_password(password),
            role=normalised_role,
        )
        return await self.user_repository.save(user)

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        return await self.user_repository.find_by_id(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        return await self.user_repository.find_by_email(email)

    async def list_users(self, *, page: int = 1, limit: int = 50, search: Optional[str] = None) -> List[User]:
        return await self.user_repository.list_all(page=page, limit=limit, search=search)

    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        user = await self.user_repository.find_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise ValueError("Invalid credentials")
        token = create_access_token(user.id)
        return {
            "token": token,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role.value,
            },
        }

    async def update_user_role(self, user_id: UUID, new_role: str) -> User:
        user = await self._get_or_raise(user_id)
        user.role = self._normalise_role(new_role)
        return await self.user_repository.save(user)

    async def delete_user(self, user_id: UUID) -> None:
        await self._get_or_raise(user_id)
        if not await self.user_repository.delete(user_id):
            raise ValueError("User could not be deleted")

    async def activate_user(self, user_id: UUID) -> User:
        user = await self._get_or_raise(user_id)
        user.is_active = True
        return await self.user_repository.save(user)

    async def deactivate_user(self, user_id: UUID) -> User:
        user = await self._get_or_raise(user_id)
        user.is_active = False
        return await self.user_repository.save(user)

    async def change_password(self, user_id: UUID, old_password: str, new_password: str) -> None:
        user = await self._get_or_raise(user_id)
        if not verify_password(old_password, user.password_hash):
            raise ValueError("Invalid credentials")
        self._validate_password_strength(new_password)
        user.password_hash = hash_password(new_password)
        await self.user_repository.save(user)

    async def update_user(self, user_id: UUID, updates: Dict[str, Any]) -> User:
        if not updates:
            raise ValueError("No updates provided")
        user = await self._get_or_raise(user_id)

        if "email" in updates:
            new_email = updates["email"]
            self._validate_email_format(new_email)
            if new_email != user.email:
                await self._ensure_email_available(new_email)
            user.email = new_email

        if "role" in updates:
            user.role = self._normalise_role(updates["role"])

        if "is_active" in updates:
            user.is_active = bool(updates["is_active"])

        forbidden = {"id", "password_hash", "created_at"}
        unknown_keys = forbidden.intersection(updates.keys())
        if unknown_keys:
            raise ValueError(f"Cannot update fields: {sorted(unknown_keys)}")

        return await self.user_repository.save(user)

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

    async def _get_or_raise(self, user_id: UUID) -> User:
        user = await self.user_repository.find_by_id(user_id)
        if user is None:
            raise ValueError(f"User with id {user_id} not found")
        return user

    def _validate_email_format(self, email: str) -> None:
        if not email or "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Invalid email format")

    async def _ensure_email_available(self, email: str) -> None:
        existing = await self.user_repository.find_by_email(email)
        if existing is not None:
            raise ValueError("Email already registered")

    def _validate_password_strength(self, password: str) -> None:
        min_length = self.settings.password_min_length
        if len(password) < min_length:
            raise ValueError(f"Password must be at least {min_length} characters long")
        if not any(c.isupper() for c in password):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in password):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain at least one number")

    def _normalise_role(self, role: str) -> UserRole:
        try:
            return UserRole(role.lower())
        except ValueError:
            valid = ", ".join(r.value for r in UserRole)
            raise ValueError(f"Invalid role. Valid roles: {valid}") from None
