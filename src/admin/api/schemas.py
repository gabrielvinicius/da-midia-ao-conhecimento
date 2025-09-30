# src/admin/api/schemas.py
from pydantic import BaseModel
from typing import Optional

from src.auth.domain.user import UserRole

class UserUpdateRequest(BaseModel):
    """Schema for updating a user's details."""
    role: Optional[UserRole] = None
