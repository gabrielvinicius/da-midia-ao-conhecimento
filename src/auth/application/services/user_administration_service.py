"""
User Administration Service - Single Responsibility: User Administration
"""
from typing import Optional
from uuid import UUID
from src.auth.domain.user import User
from src.auth.application.commands.update_user_command import UpdateUserCommand
from src.auth.application.commands.update_user_command_handler import UpdateUserCommandHandler
from src.auth.application.commands.delete_user_command import DeleteUserCommand
from src.auth.application.commands.delete_user_command_handler import DeleteUserCommandHandler


class UserAdministrationService:
    """
    Service responsible ONLY for user administration operations.
    
    Single Responsibility: Handle admin operations on users (update, delete, etc).
    """
    
    def __init__(self, 
                 update_user_handler: UpdateUserCommandHandler,
                 delete_user_handler: DeleteUserCommandHandler):
        self.update_user_handler = update_user_handler
        self.delete_user_handler = delete_user_handler
    
    async def update_user(self, user_id: UUID, **kwargs) -> User:
        """
        Update user information.
        
        Args:
            user_id: ID of user to update
            **kwargs: Fields to update (email, role, etc.)
            
        Returns:
            User: Updated user object
            
        Raises:
            ValueError: If user not found or validation fails
        """
        command = UpdateUserCommand(user_id=user_id, **kwargs)
        return await self.update_user_handler.handle(command)
    
    async def update_user_role(self, user_id: UUID, new_role: str) -> User:
        """
        Update user's role (admin operation).
        
        Args:
            user_id: ID of user to update
            new_role: New role to assign
            
        Returns:
            User: Updated user object
        """
        return await self.update_user(user_id, role=new_role)
    
    async def activate_user(self, user_id: UUID) -> User:
        """
        Activate a user account.
        
        Args:
            user_id: ID of user to activate
            
        Returns:
            User: Updated user object
        """
        return await self.update_user(user_id, is_active=True)
    
    async def deactivate_user(self, user_id: UUID) -> User:
        """
        Deactivate a user account.
        
        Args:
            user_id: ID of user to deactivate
            
        Returns:
            User: Updated user object
        """
        return await self.update_user(user_id, is_active=False)
    
    async def delete_user(self, user_id: UUID) -> None:
        """
        Permanently delete a user account.
        
        Args:
            user_id: ID of user to delete
            
        Raises:
            ValueError: If user not found or cannot be deleted
        """
        command = DeleteUserCommand(user_id=user_id)
        await self.delete_user_handler.handle(command)
    
    async def validate_admin_operation(self, admin_user: User, target_user_id: UUID) -> None:
        """
        Validate if admin operation is allowed.
        
        Args:
            admin_user: User performing the operation
            target_user_id: Target user ID
            
        Raises:
            PermissionError: If operation not allowed
        """
        if not admin_user.role or admin_user.role.value != "admin":
            raise PermissionError("Only administrators can perform this operation")
        
        if str(admin_user.id) == str(target_user_id):
            raise PermissionError("Cannot perform admin operations on yourself")