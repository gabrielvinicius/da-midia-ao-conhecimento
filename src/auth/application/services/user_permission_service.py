"""
User Permission Service - Single Responsibility: Permission Validation
Follows SRP by handling only permission-related operations.
"""
from uuid import UUID
from src.auth.domain.user import User
from src.auth.domain.interfaces import IUserPermissionService


class UserPermissionService(IUserPermissionService):
    """
    Service responsible ONLY for user permission validation.
    
    Single Responsibility: Handle permission checks and authorization logic.
    """
    
    def can_perform_admin_operation(self, admin_user: User, target_user_id: UUID) -> bool:
        """
        Check if user can perform admin operation on target user.
        
        Args:
            admin_user: User attempting the operation
            target_user_id: Target user ID
            
        Returns:
            bool: True if operation is allowed
        """
        if not admin_user.role or admin_user.role.value != "admin":
            return False
        
        # Admins cannot perform operations on themselves
        if str(admin_user.id) == str(target_user_id):
            return False
            
        return True
    
    def can_access_resource(self, user: User, resource_id: UUID, operation: str) -> bool:
        """
        Check if user can access specific resource.
        
        Args:
            user: User requesting access
            resource_id: Resource identifier
            operation: Operation type (read, write, delete)
            
        Returns:
            bool: True if access is allowed
        """
        # Basic implementation - can be extended for more complex logic
        if not user.is_active:
            return False
            
        # Admins can access everything
        if user.role and user.role.value == "admin":
            return True
            
        # Users can only access their own resources (basic rule)
        # This would be extended based on business requirements
        return str(user.id) == str(resource_id)
    
    def validate_admin_operation(self, admin_user: User, target_user_id: UUID) -> None:
        """
        Validate if admin operation is allowed, raising exception if not.
        
        Args:
            admin_user: User performing the operation
            target_user_id: Target user ID
            
        Raises:
            PermissionError: If operation not allowed
        """
        if not self.can_perform_admin_operation(admin_user, target_user_id):
            if not admin_user.role or admin_user.role.value != "admin":
                raise PermissionError("Only administrators can perform this operation")
            
            if str(admin_user.id) == str(target_user_id):
                raise PermissionError("Cannot perform admin operations on yourself")