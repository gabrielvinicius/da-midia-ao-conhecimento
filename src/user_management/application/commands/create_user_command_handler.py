from __future__ import annotations

from datetime import datetime
from typing import Any

from src.user_management.application.commands.create_user_command import (
    CreateUserCommand,
)
from src.user_management.domain.user import UserRole
from src.user_management.infrastructure.user_repository import UserRepository
from src.shared.exceptions.domain_exceptions import ValidationError

ALLOWED_ROLES = {role.value for role in UserRole}


class CreateUserCommandHandler:
    """Legacy command handler preserved for backwards compatibility."""

    def __init__(
        self,
        *,
        user_repository: UserRepository,
        user_validator: Any,
        password_service: Any,
        user_factory: Any,
    ) -> None:
        self._repository = user_repository
        self._validator = user_validator
        self._password_service = password_service
        self._user_factory = user_factory

    async def handle(self, command: CreateUserCommand):
        email = command.normalized_email()
        role = command.normalized_role()

        self._validate_email_format(email)
        await self._validator.validate_new_user(email)
        self._validate_role(role)
        self._validate_password_strength(command.password)

        if await self._repository.find_by_email(email):
            raise ValidationError("email", email, "Email already registered")

        hashed_password = self._password_service.hash_password(command.password)

        user = self._user_factory.create(email, hashed_password)
        # Ensure consistency regardless of what the factory returns.
        if hasattr(user, "email"):
            user.email = email
        if hasattr(user, "role"):
            setattr(user, "role", UserRole(role))
        if hasattr(user, "password_hash"):
            setattr(user, "password_hash", hashed_password)
        if hasattr(user, "is_active") and getattr(user, "is_active") is None:
            setattr(user, "is_active", True)
        if hasattr(user, "created_at") and getattr(user, "created_at") is None:
            setattr(user, "created_at", datetime.utcnow())

        saved_user = await self._repository.save(user)
        return saved_user

    @staticmethod
    def _validate_email_format(email: str) -> None:
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValidationError("email", email, "Invalid email format")

    @staticmethod
    def _validate_role(role: str) -> None:
        role_key = role.lower()
        if role_key not in ALLOWED_ROLES:
            raise ValidationError("role", role, "Invalid user role")

    @staticmethod
    def _validate_password_strength(password: str) -> None:
        if len(password) < 8:
            raise ValidationError("password", password, "Password does not meet security requirements")
        if not any(c.isupper() for c in password):
            raise ValidationError("password", password, "Password does not meet security requirements")
        if not any(c.islower() for c in password):
            raise ValidationError("password", password, "Password does not meet security requirements")
        if not any(c.isdigit() for c in password):
            raise ValidationError("password", password, "Password does not meet security requirements")


__all__ = ["CreateUserCommandHandler"]
