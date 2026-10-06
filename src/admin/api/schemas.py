"""Esquemas da API do administrador."""
from pydantic import BaseModel

from src.user_management.domain import UserRole


class UserUpdateRequest(BaseModel):
    """Novo perfil do usuário (obrigatório: antes, vazio virava erro 400 confuso)."""

    role: UserRole


class SystemStatsResponse(BaseModel):
    """Schema for aggregated admin statistics."""

    total_users: int
    active_users: int
    total_media: int
    processing_media: int
    failed_media: int
    completed_media: int
    success_rate: float
