"""
Admin User Service - Single Responsibility: Admin user operations
Follows SRP by handling only admin-related user management.
"""
from typing import Dict, List
from uuid import UUID

import structlog

from src.admin.domain.interfaces import IAdminUserService, IAdminAuditService
from src.user_management.domain.interfaces import IUserPermissionService
from src.user_management.domain.user import User, UserRole
from src.user_management.infrastructure.user_repository import UserRepository

logger = structlog.get_logger(__name__)


class AdminUserService(IAdminUserService):
    """
    Service responsible ONLY for admin user management operations.
    
    Single Responsibility: Handle admin operations on users.
    Open/Closed: Extensible through interface implementations.
    Dependency Inversion: Depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        user_repository: UserRepository,
        permission_service: IUserPermissionService,
        audit_service: IAdminAuditService,
    ):
        self.user_repository = user_repository
        self.permission_service = permission_service
        self.audit_service = audit_service

    async def update_user_role(self, user_id: UUID, new_role: UserRole, admin_user: User) -> User:
        """
        Update user role with proper admin validation and audit logging.
        
        Args:
            user_id: ID of user to update
            new_role: New role to assign
            admin_user: Admin user performing the operation
            
        Returns:
            User: Updated user object
            
        Raises:
            PermissionError: If admin doesn't have permission
            ValueError: If user not found or invalid role
        """
        self.permission_service.validate_admin_operation(admin_user, user_id)
        
        user = await self.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        
        try:
            role_enum = new_role if isinstance(new_role, UserRole) else UserRole(new_role)
        except ValueError as exc:
            raise ValueError(f"Invalid role: {new_role}") from exc

        old_role = user.role.value if user.role else "none"

        user.role = role_enum
        updated_user = await self.user_repository.save(user)
        
        await self.audit_service.log_admin_action(
            admin_user=admin_user,
            action="update_user_role",
            target_type="user",
            target_id=user_id,
            details={
                "old_role": old_role,
                "new_role": new_role,
                "target_email": user.email
            }
        )
        
        logger.info(
            "admin.user.role_updated",
            admin_id=str(admin_user.id),
            target_user_id=str(user_id),
            old_role=old_role,
            new_role=role_enum.value
        )

        return updated_user
    
    async def delete_user(self, user_id: UUID, admin_user: User) -> None:
        """
        Delete user with proper admin validation and audit logging.
        
        Args:
            user_id: ID of user to delete
            admin_user: Admin user performing the operation
            
        Raises:
            PermissionError: If admin doesn't have permission
            ValueError: If user not found
        """
        self.permission_service.validate_admin_operation(admin_user, user_id)
        
        user = await self.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        
        success = await self.user_repository.delete(user_id)
        if not success:
            raise ValueError("User could not be deleted")
        
        await self.audit_service.log_admin_action(
            admin_user=admin_user,
            action="delete_user",
            target_type="user",
            target_id=user_id,
            details={
                "target_email": user.email,
                "target_role": user.role.value if user.role else "none"
            }
        )
        
        logger.info(
            "admin.user.deleted",
            admin_id=str(admin_user.id),
            target_user_id=str(user_id),
            target_email=user.email
        )
    
    async def activate_user(self, user_id: UUID, admin_user: User) -> User:
        """
        Activate user account.
        
        Args:
            user_id: ID of user to activate
            admin_user: Admin user performing the operation
            
        Returns:
            User: Updated user object
        """
        self.permission_service.validate_admin_operation(admin_user, user_id)
        
        user = await self.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        
        user.is_active = True
        updated_user = await self.user_repository.save(user)
        
        await self.audit_service.log_admin_action(
            admin_user=admin_user,
            action="activate_user",
            target_type="user",
            target_id=user_id,
            details={"target_email": user.email}
        )
        
        return updated_user
    
    async def deactivate_user(self, user_id: UUID, admin_user: User) -> User:
        """
        Deactivate user account.
        
        Args:
            user_id: ID of user to deactivate
            admin_user: Admin user performing the operation
            
        Returns:
            User: Updated user object
        """
        self.permission_service.validate_admin_operation(admin_user, user_id)
        
        user = await self.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        
        user.is_active = False
        updated_user = await self.user_repository.save(user)
        
        await self.audit_service.log_admin_action(
            admin_user=admin_user,
            action="deactivate_user",
            target_type="user",
            target_id=user_id,
            details={"target_email": user.email}
        )
        
        return updated_user
    
    async def bulk_update_users(self, user_updates: List[Dict], admin_user: User) -> List[User]:
        """
        Update multiple users in bulk.
        
        Args:
            user_updates: List of user update dictionaries
            admin_user: Admin user performing the operation
            
        Returns:
            List[User]: List of updated users
        """
        updated_users = []
        
        for update_data in user_updates:
            user_id = update_data.get("user_id")
            new_role = update_data.get("role")
            is_active = update_data.get("is_active")
            
            if not user_id:
                continue

            try:
                if new_role:
                    user = await self.update_user_role(user_id, new_role, admin_user)
                    updated_users.append(user)
                
                if is_active is not None:
                    if is_active:
                        user = await self.activate_user(user_id, admin_user)
                    else:
                        user = await self.deactivate_user(user_id, admin_user)
                    updated_users.append(user)
                    
            except (ValueError, PermissionError) as e:
                logger.warning(
                    "admin.bulk_update.failed",
                    user_id=str(user_id),
                    error=str(e),
                    admin_id=str(admin_user.id)
                )
                continue
        
        return updated_users
