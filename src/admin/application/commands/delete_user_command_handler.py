# src/admin/application/commands/delete_user_command_handler.py
from src.auth.domain.interfaces import IUserRepository
from .delete_user_command import DeleteUserCommand


class DeleteUserCommandHandler:
    """
    Delete User Command Handler following SOLID principles.
    
    Single Responsibility: Handle user deletion command.
    Dependency Inversion: Depends on IUserRepository abstraction.
    """
    
    def __init__(self, user_repository: IUserRepository):
        self.user_repository = user_repository

    async def handle(self, command: DeleteUserCommand) -> None:
        """
        Handles the user deletion process.
        
        Args:
            command: Delete user command containing user_id
            
        Raises:
            ValueError: If user not found or could not be deleted
        """
        success = await self.user_repository.delete(command.user_id)
        if not success:
            raise ValueError("User not found or could not be deleted.")
