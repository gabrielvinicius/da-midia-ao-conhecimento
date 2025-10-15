# src/admin/api/schemas.py
from pydantic import BaseModel
from typing import Optional

from src.auth.domain.user import UserRole

class UserUpdateRequest(BaseModel):
    """Schema for updating a user's details."""
    role: Optional[UserRole] = None


class SystemStatsResponse(BaseModel):
    """Schema for system statistics response."""
    total_users: int
    total_media: int
    total_transcriptions: int
    total_summaries: int
    active_tasks: int
    system_uptime: str
    database_status: str
    redis_status: str
