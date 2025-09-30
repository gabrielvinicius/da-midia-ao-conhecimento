# src/auth/application/commands/update_user_command.py
from dataclasses import dataclass
from uuid import UUID
from typing import Optional

from src.auth.domain.user import UserRole

@dataclass(frozen=True)
class UpdateUserCommand:
    """Command to update a user's details."""
    user_id: UUID
    role: Optional[UserRole] = None
