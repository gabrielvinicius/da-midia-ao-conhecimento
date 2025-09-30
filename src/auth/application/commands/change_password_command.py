# src/auth/application/commands/change_password_command.py
from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class ChangePasswordCommand:
    """Command to change a user's password."""
    user_id: UUID
    old_password: str
    new_password: str
