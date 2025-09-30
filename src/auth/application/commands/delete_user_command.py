# src/auth/application/commands/delete_user_command.py
from dataclasses import dataclass
from uuid import UUID

@dataclass(frozen=True)
class DeleteUserCommand:
    """Command to delete a user."""
    user_id: UUID
