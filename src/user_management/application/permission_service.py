# src/auth/application/services/permission_service.py
from uuid import UUID

from src.user_management.domain.interfaces import IUserPermissionService
from src.user_management.domain.user import User, UserRole


class UserPermissionService(IUserPermissionService):
    def validate_admin_operation(self, admin_user: User, target_user_id: UUID) -> None:
        role_value = admin_user.role.value if admin_user.role else ""
        if role_value.upper() != UserRole.ADMIN.value:
            raise PermissionError("Only administrators can perform this operation.")

        if admin_user.id == target_user_id:
            raise PermissionError("Administrators cannot perform this operation on themselves.")
