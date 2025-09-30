# src/auth/application/commands/delete_user_command_handler.py
import structlog
from src.auth.infrastructure.user_repository import UserRepository
from .delete_user_command import DeleteUserCommand

logger = structlog.get_logger(__name__)

class DeleteUserCommandHandler:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def handle(self, command: DeleteUserCommand) -> bool:
        """Handles the user deletion process."""
        logger.info("user.deletion.started", user_id=str(command.user_id))

        user_to_delete = await self.user_repository.find_by_id(command.user_id)
        if not user_to_delete:
            raise ValueError(f"User with id {command.user_id} not found.")

        # Optional: Add business logic here, e.g., prevent deleting an admin or oneself.

        success = await self.user_repository.delete(command.user_id)
        if success:
            logger.info("user.deletion.completed", user_id=str(command.user_id))
        else:
            # This case should ideally not be reached if the find_by_id check passed
            logger.warning("user.deletion.failed", user_id=str(command.user_id), reason="User disappeared after initial check.")
        
        return success
