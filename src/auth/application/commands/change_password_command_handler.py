# src/auth/application/commands/change_password_command_handler.py
import structlog

from src.auth.infrastructure.user_repository import UserRepository
from src.auth.domain.user import User
from src.shared.utils.password_utils import hash_password, verify_password
from .change_password_command import ChangePasswordCommand

logger = structlog.get_logger(__name__)

class ChangePasswordCommandHandler:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def handle(self, command: ChangePasswordCommand) -> User:
        """Handles the secure password change process."""
        logger.info("user.password_change.started", user_id=str(command.user_id))

        user = await self.user_repository.find_by_id(command.user_id)
        if not user:
            raise ValueError(f"User with id {command.user_id} not found.")

        # 1. Verify the old password
        if not verify_password(command.old_password, user.password_hash):
            logger.warning("user.password_change.failed", user_id=str(command.user_id), reason="Invalid old password")
            raise ValueError("Invalid old password.")

        # 2. Hash the new password
        new_hashed_password = hash_password(command.new_password)
        user.password_hash = new_hashed_password

        # 3. Save the updated user
        updated_user = await self.user_repository.save(user)
        logger.info("user.password_change.completed", user_id=str(command.user_id))

        return updated_user
