# src/auth/application/services/permission_service.py
from uuid import UUID

from src.user_management.domain.interfaces import IUserPermissionService
from src.user_management.domain.user import User


class UserPermissionService(IUserPermissionService):
    def validate_admin_operation(self, admin_user: User, target_user_id: UUID) -> None:
        if not admin_user.role or admin_user.role.value != "admin":
            raise PermissionError("Only administrators can perform this operation.")

        if admin_user.id == target_user_id:
            raise PermissionError("Administrators cannot perform this operation on themselves.")
