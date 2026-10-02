from uuid import UUID

from src.user_management.application.ports import PermissionServicePort
from src.user_management.domain import User, UserRole


class UserPermissionService(PermissionServicePort):
    def require_admin(self, admin_user: User) -> None:
        role_value = admin_user.role.value if admin_user.role else ""
        if role_value.upper() != UserRole.ADMIN.value:
            raise PermissionError("Apenas administradores podem executar esta operação.")

    def validate_admin_operation(self, admin_user: User, target_user_id: UUID) -> None:
        """Operação de um admin sobre uma conta: nunca sobre a própria (não se
        rebaixa, desativa nem exclui por engano)."""
        self.require_admin(admin_user)
        if admin_user.id == target_user_id:
            raise PermissionError("Um administrador não pode fazer isso com a própria conta.")
