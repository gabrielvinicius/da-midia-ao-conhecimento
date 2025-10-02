# src/auth/application/auth_service.py
from typing import Optional
from uuid import UUID

from src.auth.domain.user import User, UserRole
# Import all commands and handlers
from .commands.create_user_command import CreateUserCommand
from .commands.create_user_command_handler import CreateUserCommandHandler
from .commands.authenticate_user_command import AuthenticateUserCommand
from .commands.authenticate_user_command_handler import AuthenticateUserCommandHandler
from .commands.update_user_command import UpdateUserCommand
from .commands.update_user_command_handler import UpdateUserCommandHandler
from .commands.delete_user_command import DeleteUserCommand
from .commands.delete_user_command_handler import DeleteUserCommandHandler


class AuthService:
    """Facade service to dispatch authentication and user management commands."""
    def __init__(
        self,
        create_user_handler: CreateUserCommandHandler,
        authenticate_user_handler: AuthenticateUserCommandHandler,
        update_user_handler: UpdateUserCommandHandler, # Admin action
        delete_user_handler: DeleteUserCommandHandler,       # Admin action
    ):
        self.create_user_handler = create_user_handler
        self.authenticate_user_handler = authenticate_user_handler
        self.update_user_handler = update_user_handler
        self.delete_user_handler = delete_user_handler

    async def create_user(self, email: str, password: str) -> User:
        command = CreateUserCommand(email=email, password=password)
        return await self.create_user_handler.handle(command)

    async def authenticate_user_and_get_token(self, email: str, password: str) -> Optional[str]:
        command = AuthenticateUserCommand(email=email, password=password)
        return await self.authenticate_user_handler.handle(command)

    # --- Admin Methods ---

    async def update_user(self, user_id: UUID, **kwargs) -> User:
        """Dispatches the UpdateUserCommand."""
        command = UpdateUserCommand(user_id=user_id, **kwargs)
        return await self.update_user_handler.handle(command)

    async def delete_user(self, user_id: UUID) -> None:
        """Dispatches the DeleteUserCommand."""
        command = DeleteUserCommand(user_id=user_id)
        await self.delete_user_handler.handle(command)
