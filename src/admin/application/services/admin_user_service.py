"""Admin-specific user management service."""

from uuid import UUID

import structlog

from src.admin.application.ports import AdminUserRepositoryPort
from src.admin.application.ports import AdminAuditPort
from src.user_management.application.ports import PermissionServicePort
from src.user_management.domain import User, UserRole

logger = structlog.get_logger(__name__)


class AdminUserService:
    """Handle admin operations over users with permission and audit checks."""

    def __init__(
        self,
        user_repository: AdminUserRepositoryPort,
        permission_service: PermissionServicePort,
        audit_service: AdminAuditPort,
    ) -> None:
        self.user_repository = user_repository
        self.permission_service = permission_service
        self.audit_service = audit_service

    async def update_user_role(
        self,
        user_id: UUID,
        new_role: UserRole,
        admin_user: User,
    ) -> User:
        self.permission_service.validate_admin_operation(admin_user, user_id)

        user = await self.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        role_enum = new_role if isinstance(new_role, UserRole) else UserRole(new_role)
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
                "new_role": role_enum.value,
                "target_email": user.email,
            },
        )

        logger.info(
            "admin.user.role_updated",
            admin_id=str(admin_user.id),
            target_user_id=str(user_id),
            old_role=old_role,
            new_role=role_enum.value,
        )

        return updated_user

    async def delete_user(self, user_id: UUID, admin_user: User) -> None:
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
                "target_role": user.role.value if user.role else "none",
            },
        )

        logger.info(
            "admin.user.deleted",
            admin_id=str(admin_user.id),
            target_user_id=str(user_id),
        )
