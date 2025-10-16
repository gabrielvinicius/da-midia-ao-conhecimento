# src/auth/application/auth_service.py
from typing import Optional
from uuid import UUID

from src.auth.domain.user import User, UserRole
from src.auth.infrastructure.user_repository import UserRepository
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
        user_repository: UserRepository,
    ):
        self.create_user_handler = create_user_handler
        self.authenticate_user_handler = authenticate_user_handler
        self.update_user_handler = update_user_handler
        self.delete_user_handler = delete_user_handler
        self.user_repository = user_repository

    async def create_user(self, email: str, password: str) -> User:
        command = CreateUserCommand(email=email, password=password)
        return await self.create_user_handler.handle(command)

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticates a user and returns the user object if successful."""
        command = AuthenticateUserCommand(email=email, password=password)
        token = await self.authenticate_user_handler.handle(command)
        if token:
            return await self.user_repository.find_by_email(email)
        return None

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

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        try:
            return await self.user_repository.find_by_id(UUID(user_id))
        except ValueError:
            return None

    async def change_password(self, user_id: UUID, old_password: str, new_password: str) -> None:
        """Change user password."""
        from .commands.change_password_command import ChangePasswordCommand
        from .commands.change_password_command_handler import ChangePasswordCommandHandler
        
        # For now, we'll implement this directly
        user = await self.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        # Verify old password
        from src.shared.utils.password_utils import verify_password, hash_password
        if not verify_password(old_password, user.hashed_password):
            raise ValueError("Invalid old password")
        
        # Update password
        user.hashed_password = hash_password(new_password)
        await self.user_repository.save(user)
