# src/admin/api/schemas.py
from typing import Optional

from pydantic import BaseModel

from src.user_management.domain import UserRole


class UserUpdateRequest(BaseModel):
    """Schema for updating a user's details."""

    role: Optional[UserRole] = None


class SystemStatsResponse(BaseModel):
    """Schema for aggregated admin statistics."""

    total_users: int
    active_users: int
    total_media: int
    processing_media: int
    failed_media: int
    completed_media: int
    success_rate: float
