# src/admin/application/commands/delete_user_command_handler.py
from src.auth.infrastructure.user_repository import UserRepository
from .delete_user_command import DeleteUserCommand

class DeleteUserCommandHandler:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def handle(self, command: DeleteUserCommand) -> None:
        """Handles the user deletion process."""
        success = await self.user_repository.delete(command.user_id)
        if not success:
            raise ValueError("User not found or could not be deleted.")
