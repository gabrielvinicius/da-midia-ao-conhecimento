"""Admin-specific user management service."""

from typing import List, Optional, Any
from uuid import UUID

import structlog

from src.admin.application.ports import AdminAuditPort
from src.admin.application.ports import UserAdminPort
from src.user_management.application.ports import PermissionServicePort
from src.user_management.domain import User, UserRole

logger = structlog.get_logger(__name__)


class AdminUserService:
    """Handle admin operations over users with permission and audit checks."""

    def __init__(
        self,
        user_service: UserAdminPort, # Use the Port
        permission_service: PermissionServicePort,
        audit_service: AdminAuditPort,
    ) -> None:
        self.user_service = user_service
        self.permission_service = permission_service
        self.audit_service = audit_service

    async def update_user_role(
        self,
        user_id: UUID,
        new_role: UserRole,
        admin_user: User,
    ) -> User:
        self.permission_service.validate_admin_operation(admin_user, user_id)

        updated_user = await self.user_service.update_user_role(
            user_id=user_id,
            new_role=new_role,
            admin_user=admin_user,
        )

        await self.audit_service.log_admin_action(
            admin_user=admin_user,
            action="update_user_role",
            target_type="user",
            target_id=user_id,
            details={
                "old_role": "unknown", # Port simplified
                "new_role": new_role.value if hasattr(new_role, 'value') else str(new_role),
                "target_email": updated_user.email,
            },
        )

        return updated_user

    async def delete_user(self, user_id: UUID, admin_user: User) -> None:
        self.permission_service.validate_admin_operation(admin_user, user_id)

        await self.user_service.delete_user(user_id=user_id, admin_user=admin_user)

        await self.audit_service.log_admin_action(
            admin_user=admin_user,
            action="delete_user",
            target_type="user",
            target_id=user_id,
            details={
                "target_id": str(user_id),
            },
        )

    async def list_users(self, query: Any) -> dict:
        # Permission check for listing might be higher level (API) but service can double check
        return await self.user_service.list_users(query)

    async def activate_user(self, user_id: UUID, admin_user: User) -> User:
        self.permission_service.validate_admin_operation(admin_user, user_id)
        user = await self.user_service.activate_user(user_id, admin_user)
        
        await self.audit_service.log_admin_action(
            admin_user=admin_user,
            action="activate_user",
            target_type="user",
            target_id=user_id,
        )
        return user

    async def deactivate_user(self, user_id: UUID, admin_user: User) -> User:
        self.permission_service.validate_admin_operation(admin_user, user_id)
        user = await self.user_service.deactivate_user(user_id, admin_user)
        
        await self.audit_service.log_admin_action(
            admin_user=admin_user,
            action="deactivate_user",
            target_type="user",
            target_id=user_id,
        )
        return user

