# src/admin/application/commands/update_user_role_command.py
from dataclasses import dataclass
from uuid import UUID
from src.auth.domain.user import UserRole

@dataclass(frozen=True)
class UpdateUserRoleCommand:
    user_id: UUID
    new_role: UserRole
