# src/admin/application/commands/update_user_role_command_handler.py
from src.auth.infrastructure.user_repository import UserRepository
from .update_user_role_command import UpdateUserRoleCommand
from src.auth.domain.user import User

class UpdateUserRoleCommandHandler:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def handle(self, command: UpdateUserRoleCommand) -> User:
        """Handles the user role update process."""
        user = await self.user_repository.find_by_id(command.user_id)
        if not user:
            raise ValueError("User not found.")

        user.role = command.new_role
        return await self.user_repository.save(user)
