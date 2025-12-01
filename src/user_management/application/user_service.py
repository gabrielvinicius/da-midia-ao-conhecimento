from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from src.shared.utils.id_generator import generate_id
from src.shared.utils.password_utils import hash_password, verify_password
from src.shared.config.settings import Settings, settings
from src.user_management.domain.user import User, UserRole
from src.user_management.domain.exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
    InvalidCredentialsError
)
from src.user_management.infrastructure.user_repository import UserRepository
from src.user_management.utils.token import create_access_token


class UserService:
    """Unified user service (create, fetch)."""

    def __init__(self, user_repository: UserRepository, settings: Optional[Settings] = None) -> None:
        self.user_repository = user_repository
        self.settings = settings or Settings()

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

    def create_user_sync(self, email: str, password: str, role: str = "user") -> User:
        self._validate_email_format(email)
        self._ensure_email_available_sync(email)
        self._validate_password_strength(password)
        normalised_role = self._normalise_role(role)

        user = User(
            id=generate_id(),
            email=email,
            password_hash=hash_password(password),
            role=normalised_role,
        )
        return self.user_repository.save_sync(user)

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        return await self.user_repository.find_by_id(user_id)

    def get_user_by_id_sync(self, user_id: UUID) -> Optional[User]:
        return self.user_repository.find_by_id_sync(user_id)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        return await self.user_repository.find_by_email(email)

    def get_user_by_email_sync(self, email: str) -> Optional[User]:
        return self.user_repository.find_by_email_sync(email)

    async def list_users(self, *, page: int = 1, limit: int = 50, search: Optional[str] = None) -> List[User]:
        return await self.user_repository.list_all(page=page, limit=limit, search=search)

    def list_users_sync(self, *, page: int = 1, limit: int = 50, search: Optional[str] = None) -> List[User]:
        return self.user_repository.list_all_sync(page=page, limit=limit, search=search)

    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        user = await self.user_repository.find_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
        token = create_access_token(user.id)
        return {
            "token": token,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role.value,
            },
        }

    def authenticate_user_sync(self, email: str, password: str) -> Dict[str, Any]:
        user = self.user_repository.find_by_email_sync(email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError()
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

    def update_user_role_sync(self, user_id: UUID, new_role: str) -> User:
        user = self._get_or_raise_sync(user_id)
        user.role = self._normalise_role(new_role)
        return self.user_repository.save_sync(user)

    async def delete_user(self, user_id: UUID) -> None:
        await self._get_or_raise(user_id)
        if not await self.user_repository.delete(user_id):
            raise ValueError("User could not be deleted") # Keep generic for system errors

    def delete_user_sync(self, user_id: UUID) -> None:
        self._get_or_raise_sync(user_id)
        if not self.user_repository.delete_sync(user_id):
            raise ValueError("User could not be deleted")

    async def activate_user(self, user_id: UUID) -> User:
        user = await self._get_or_raise(user_id)
        user.is_active = True
        return await self.user_repository.save(user)

    def activate_user_sync(self, user_id: UUID) -> User:
        user = self._get_or_raise_sync(user_id)
        user.is_active = True
        return self.user_repository.save_sync(user)

    async def deactivate_user(self, user_id: UUID) -> User:
        user = await self._get_or_raise(user_id)
        user.is_active = False
        return await self.user_repository.save(user)

    def deactivate_user_sync(self, user_id: UUID) -> User:
        user = self._get_or_raise_sync(user_id)
        user.is_active = False
        return self.user_repository.save_sync(user)

    async def change_password(self, user_id: UUID, old_password: str, new_password: str) -> None:
        user = await self._get_or_raise(user_id)
        if not verify_password(old_password, user.password_hash):
            raise InvalidCredentialsError()
        self._validate_password_strength(new_password)
        user.password_hash = hash_password(new_password)
        await self.user_repository.save(user)

    def change_password_sync(self, user_id: UUID, old_password: str, new_password: str) -> None:
        user = self._get_or_raise_sync(user_id)
        if not verify_password(old_password, user.password_hash):
            raise InvalidCredentialsError()
        self._validate_password_strength(new_password)
        user.password_hash = hash_password(new_password)
        self.user_repository.save_sync(user)

    async def ensure_admin_user(
        self,
        *,
        email: str,
        default_password: str,
        force_password_reset: bool = False,
    ) -> User:
        """Ensure that ``email`` is associated with an admin account.

        Creates the user if needed or elevates the existing account role. Optionally
        resets the password so staging environments keep deterministic credentials.
        """

        normalised_email = email.strip().lower()
        if not normalised_email:
            raise ValueError("Admin email must not be empty")

        self._validate_password_strength(default_password)

        existing = await self.user_repository.find_by_email(normalised_email)
        if existing is None:
            return await self.create_user(normalised_email, default_password, role=UserRole.ADMIN.value)

        updated = False
        if existing.role != UserRole.ADMIN:
            existing.role = UserRole.ADMIN
            updated = True

        if force_password_reset:
            existing.password_hash = hash_password(default_password)
            updated = True

        if updated:
            return await self.user_repository.save(existing)

        return existing

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

    def update_user_sync(self, user_id: UUID, updates: Dict[str, Any]) -> User:
        if not updates:
            raise ValueError("No updates provided")
        user = self._get_or_raise_sync(user_id)

        if "email" in updates:
            new_email = updates["email"]
            self._validate_email_format(new_email)
            if new_email != user.email:
                self._ensure_email_available_sync(new_email)
            user.email = new_email

        if "role" in updates:
            user.role = self._normalise_role(updates["role"])

        if "is_active" in updates:
            user.is_active = bool(updates["is_active"])

        forbidden = {"id", "password_hash", "created_at"}
        unknown_keys = forbidden.intersection(updates.keys())
        if unknown_keys:
            raise ValueError(f"Cannot update fields: {sorted(unknown_keys)}")

        return self.user_repository.save_sync(user)

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
            raise UserNotFoundError(str(user_id))
        return user

    def _get_or_raise_sync(self, user_id: UUID) -> User:
        user = self.user_repository.find_by_id_sync(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))
        return user

    def _validate_email_format(self, email: str) -> None:
        if not email or "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Invalid email format")

    async def _ensure_email_available(self, email: str) -> None:
        existing = await self.user_repository.find_by_email(email)
        if existing is not None:
            raise UserAlreadyExistsError(email)

    def _ensure_email_available_sync(self, email: str) -> None:
        existing = self.user_repository.find_by_email_sync(email)
        if existing is not None:
            raise UserAlreadyExistsError(email)

    def _validate_password_strength(self, password: str) -> None:
        min_length = self.settings.AUTH_PASSWORD_MIN_LENGTH
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
            return UserRole(role.upper())
        except ValueError:
            valid = ", ".join(r.value for r in UserRole)
            raise ValueError(f"Invalid role. Valid roles: {valid}") from None
