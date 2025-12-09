from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from src.shared.utils.password_utils import hash_password, verify_password
from src.shared.infrastructure.config.settings import Settings, settings
from src.user_management.domain.user import User, UserRole
from src.user_management.domain.exceptions import (
    UserAlreadyExistsError,
    UserNotFoundError,
    InvalidCredentialsError
)
from src.user_management.infrastructure.repositories.sqlalchemy_user_repository import UserRepository
from src.user_management.utils.token import create_access_token
from src.user_management.application.commands.dto import CreateUserCommand, UpdateUserCommand, DeleteUserCommand
from src.user_management.application.queries.dto import GetUserQuery, ListUsersQuery
from src.user_management.application.auth_queries import AuthQueries


class UserService:
    """Unified user service for command operations."""

    def __init__(
        self,
        user_repository: UserRepository,
        auth_queries: AuthQueries,
        settings: Optional[Settings] = None
    ) -> None:
        self.user_repository = user_repository
        self.auth_queries = auth_queries
        self.settings = settings or Settings()

    async def create_user(self, command: CreateUserCommand) -> User:
        await self._ensure_email_available(command.email)
        self._validate_password_strength(command.password)
        normalised_role = self._normalise_role(command.role.value)

        user = User.create(
            email=command.email,
            password_hash=hash_password(command.password),
            role=normalised_role,
        )
        return await self.user_repository.save(user)

    async def register_user(self, command: CreateUserCommand) -> dict[str, object]:
        user = await self.create_user(command)
        return {
            "success": True,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role.value,
            },
        }
    
    async def update_user(self, command: UpdateUserCommand) -> User:
        if not command.email and not command.password and not command.role and command.is_active is None:
            raise ValueError("No updates provided")
        
        user = await self._get_or_raise(command.user_id)

        if command.email:
            self._validate_email_format(command.email)
            if command.email != user.email:
                await self._ensure_email_available(command.email)
            user.email = command.email

        if command.role:
            user.role = self._normalise_role(command.role.value)

        if command.is_active is not None:
            user.is_active = command.is_active
        
        if command.password: # Should be handled by change_password command
            self._validate_password_strength(command.password)
            user.password_hash = hash_password(command.password)

        return await self.user_repository.save(user)

    async def delete_user(self, command: DeleteUserCommand) -> None:
        await self._get_or_raise(command.user_id)
        if not await self.user_repository.delete(command.user_id):
            raise ValueError("User could not be deleted")
            
    async def activate_user(self, command: GetUserQuery) -> User: # Re-using GetUserQuery for user_id
        user = await self._get_or_raise(command.user_id)
        user.is_active = True
        return await self.user_repository.save(user)

    async def deactivate_user(self, command: GetUserQuery) -> User: # Re-using GetUserQuery for user_id
        user = await self._get_or_raise(command.user_id)
        user.is_active = False
        return await self.user_repository.save(user)

    async def change_password(self, user_id: UUID, old_password: str, new_password: str) -> None:
        # This can be made into a ChangePasswordCommand DTO
        user = await self._get_or_raise(user_id)
        if not verify_password(old_password, user.password_hash):
            raise InvalidCredentialsError()
        self._validate_password_strength(new_password)
        user.password_hash = hash_password(new_password)
        await self.user_repository.save(user)

    async def ensure_admin_user(
        self,
        *,
        email: str,
        default_password: str,
        force_password_reset: bool = False,
    ) -> User:
        normalised_email = email.strip().lower()
        if not normalised_email:
            raise ValueError("Admin email must not be empty")

        self._validate_password_strength(default_password)

        existing = await self.auth_queries.get_user_by_email(normalised_email)
        if existing is None:
            return await self.create_user(CreateUserCommand(email=normalised_email, password=default_password, role=UserRole.ADMIN))

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

    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        user = await self.auth_queries.get_user_by_email(email)
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

    async def _get_or_raise(self, user_id: UUID) -> User:
        user = await self.auth_queries.get_user_by_id(user_id)
        if user is None:
            raise UserNotFoundError(str(user_id))
        return user

    def _validate_email_format(self, email: str) -> None:
        # Simple email format validation, ideally use pydantic's EmailStr
        if not email or "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Invalid email format")

    async def _ensure_email_available(self, email: str) -> None:
        existing = await self.auth_queries.get_user_by_email(email)
        if existing is not None:
            raise UserAlreadyExistsError(email)

    def _validate_password_strength(self, password: str) -> None:
        min_length = self.settings.auth_password_min_length
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