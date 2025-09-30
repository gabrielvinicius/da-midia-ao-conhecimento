# src/auth/application/auth_service.py
from typing import Optional
from uuid import UUID

from src.auth.domain.user import User, UserRole
from .commands.create_user_command import CreateUserCommand
from .commands.create_user_command_handler import CreateUserCommandHandler
from .commands.authenticate_user_command import AuthenticateUserCommand
from .commands.authenticate_user_command_handler import AuthenticateUserCommandHandler
from .commands.delete_user_command import DeleteUserCommand
from .commands.delete_user_command_handler import DeleteUserCommandHandler
from .commands.update_user_command import UpdateUserCommand
from .commands.update_user_command_handler import UpdateUserCommandHandler
from .commands.change_password_command import ChangePasswordCommand # Import new command
from .commands.change_password_command_handler import ChangePasswordCommandHandler # Import new handler


class AuthService:
    """Facade service to dispatch authentication commands."""
    def __init__(
        self,
        create_user_handler: CreateUserCommandHandler,
        authenticate_user_handler: AuthenticateUserCommandHandler,
        delete_user_handler: DeleteUserCommandHandler,
        update_user_handler: UpdateUserCommandHandler,
        change_password_handler: ChangePasswordCommandHandler, # Added dependency
    ):
        self.create_user_handler = create_user_handler
        self.authenticate_user_handler = authenticate_user_handler
        self.delete_user_handler = delete_user_handler
        self.update_user_handler = update_user_handler
        self.change_password_handler = change_password_handler # Store dependency

    async def create_user(self, email: str, password: str) -> User:
        command = CreateUserCommand(email=email, password=password)
        return await self.create_user_handler.handle(command)

    async def authenticate_user_and_get_token(self, email: str, password: str) -> Optional[str]:
        command = AuthenticateUserCommand(email=email, password=password)
        return await self.authenticate_user_handler.handle(command)

    async def delete_user(self, user_id: UUID) -> bool:
        command = DeleteUserCommand(user_id=user_id)
        return await self.delete_user_handler.handle(command)

    async def update_user(self, user_id: UUID, role: Optional[UserRole] = None) -> User:
        command = UpdateUserCommand(user_id=user_id, role=role)
        return await self.update_user_handler.handle(command)

    async def change_password(self, user_id: UUID, old_password: str, new_password: str) -> User:
        """Dispatches the ChangePasswordCommand."""
        command = ChangePasswordCommand(user_id=user_id, old_password=old_password, new_password=new_password)
        return await self.change_password_handler.handle(command)
