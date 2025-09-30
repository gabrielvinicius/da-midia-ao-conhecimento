# src/auth/application/commands/update_user_command_handler.py
import structlog
from src.auth.infrastructure.user_repository import UserRepository
from src.auth.domain.user import User
from .update_user_command import UpdateUserCommand

logger = structlog.get_logger(__name__)

class UpdateUserCommandHandler:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def handle(self, command: UpdateUserCommand) -> User:
        """Handles the user update process."""
        logger.info("user.update.started", user_id=str(command.user_id))

        user_to_update = await self.user_repository.find_by_id(command.user_id)
        if not user_to_update:
            raise ValueError(f"User with id {command.user_id} not found.")

        # Update fields if they are provided in the command
        if command.role is not None:
            user_to_update.role = command.role
            logger.info("user.update.role_changed", user_id=str(command.user_id), new_role=command.role.value)

        # Save the updated user
        updated_user = await self.user_repository.save(user_to_update)
        logger.info("user.update.completed", user_id=str(command.user_id))

        return updated_user
