# src/auth/application/auth_service.py
from typing import Optional
from uuid import UUID

from src.auth.domain.user import User
from .commands.create_user_command import CreateUserCommand
from .commands.create_user_command_handler import CreateUserCommandHandler
from .commands.authenticate_user_command import AuthenticateUserCommand
from .commands.authenticate_user_command_handler import AuthenticateUserCommandHandler
from .commands.delete_user_command import DeleteUserCommand
from .commands.delete_user_command_handler import DeleteUserCommandHandler


class AuthService:
    """Facade service to dispatch authentication commands."""
    def __init__(
        self,
        create_user_handler: CreateUserCommandHandler,
        authenticate_user_handler: AuthenticateUserCommandHandler,
        delete_user_handler: DeleteUserCommandHandler, # Added dependency
    ):
        self.create_user_handler = create_user_handler
        self.authenticate_user_handler = authenticate_user_handler
        self.delete_user_handler = delete_user_handler # Store dependency

    async def create_user(self, email: str, password: str) -> User:
        """Dispatches the CreateUserCommand."""
        command = CreateUserCommand(email=email, password=password)
        return await self.create_user_handler.handle(command)

    async def authenticate_user_and_get_token(self, email: str, password: str) -> Optional[str]:
        """Dispatches the AuthenticateUserCommand and returns a token."""
        command = AuthenticateUserCommand(email=email, password=password)
        return await self.authenticate_user_handler.handle(command)

    async def delete_user(self, user_id: UUID) -> bool:
        """Dispatches the DeleteUserCommand."""
        command = DeleteUserCommand(user_id=user_id)
        return await self.delete_user_handler.handle(command)
