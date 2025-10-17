# src/admin/application/commands/update_user_role_command_handler.py
import structlog

from src.auth.domain.interfaces import IUserRepository
from src.auth.domain.user import User, UserRole
from .update_user_role_command import UpdateUserRoleCommand

logger = structlog.get_logger(__name__)


class UpdateUserRoleCommandHandler:
    """
    Update User Role Command Handler following SOLID principles.
    
    Single Responsibility: Handle user role update command.
    Dependency Inversion: Depends on IUserRepository abstraction.
    """
    
    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository

    async def handle(self, command: UpdateUserRoleCommand) -> User:
        """
        Handles the user role update process with validation.
        
        Args:
            command: Update user role command
            
        Returns:
            User: Updated user object
            
        Raises:
            ValueError: If user not found or invalid role
        """
        # Find user
        user = await self.user_repository.find_by_id(command.user_id)
        if not user:
            raise ValueError(f"User with id {command.user_id} not found")

        # Validate role
        if isinstance(command.new_role, str):
            try:
                role_enum = UserRole(command.new_role)
            except ValueError:
                raise ValueError(f"Invalid role: {command.new_role}")
        else:
            role_enum = command.new_role

        old_role = user.role.value if user.role else "none"
        
        # Update role
        user.role = role_enum
        updated_user = await self.user_repository.save(user)
        
        logger.info(
            "admin.user.role_updated",
            user_id=str(command.user_id),
            old_role=old_role,
            new_role=role_enum.value
        )
        
        return updated_user
