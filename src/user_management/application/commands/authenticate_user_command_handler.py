from __future__ import annotations

from typing import Optional

from passlib.context import CryptContext

from src.user_management.application.commands.authenticate_user_command import (
    AuthenticateUserCommand,
)
from src.user_management.config.settings import AuthSettings
from src.user_management.infrastructure.user_repository import UserRepository
from src.user_management.utils.token import create_access_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthenticateUserCommandHandler:
    """Thin wrapper kept for backwards compatibility with the old CQRS layer."""

    def __init__(
        self,
        *,
        user_repository: UserRepository,
        settings: Optional[AuthSettings] = None,
    ) -> None:
        self._repository = user_repository
        self._settings = settings or AuthSettings()

    async def handle(self, command: AuthenticateUserCommand) -> Optional[str]:
        user = await self._repository.find_by_email(command.email)
        if user is None:
            return None

        if not pwd_context.verify(command.password, user.password_hash):
            return None

        return create_access_token(user.id)


__all__ = ["AuthenticateUserCommandHandler", "pwd_context"]
