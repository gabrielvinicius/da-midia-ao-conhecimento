"""Carga do hardware para a interface.

Antes era pública: qualquer um, sem login, via CPU, memória e GPU do
servidor. Agora exige login; o nível de carga (para o aviso de fila lenta)
vai a todos, e os números só a administradores.
"""
from fastapi import APIRouter, Depends

from src.shared.infrastructure.monitoring.hardware_advisor import HardwareAdvisor
from src.user_management.api.dependencies import get_current_user
from src.user_management.domain import User, UserRole

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/ping", summary="Resposta mínima (a API está no ar?)")
async def ping() -> dict:
    return {"status": "ok"}


@router.get("/system-status", summary="Nível de carga da máquina")
async def get_system_status(current_user: User = Depends(get_current_user)) -> dict:
    advisor = HardwareAdvisor()
    status = {"pressure": advisor.recommend_strategy().value}
    if current_user.role == UserRole.ADMIN:
        stats = advisor.get_current_stats()
        status.update(
            cpu_usage=stats.cpu_usage,
            ram_usage=stats.ram_usage,
            gpu_vram_usage=stats.gpu_vram_usage,
            gpu_utilization=stats.gpu_utilization,
        )
    return status


__all__ = ["router"]
