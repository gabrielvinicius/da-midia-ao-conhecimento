from fastapi import APIRouter, Depends
from src.shared.infrastructure.monitoring.hardware_advisor import HardwareAdvisor, SystemPressure

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/ping")
async def ping() -> dict:
    return {"status": "ok"}


@router.get("/system-status")
async def get_system_status():
    """Level 6.0: Real-time hardware health and pressure advisor."""
    advisor = HardwareAdvisor()
    stats = advisor.get_current_stats()
    strategy = advisor.recommend_strategy()
    
    return {
        "pressure": strategy.value,
        "cpu_usage": stats.cpu_usage,
        "ram_usage": stats.ram_usage,
        "gpu_vram_usage": stats.gpu_vram_usage,
        "timestamp": stats.gpu_utilization # Just for consistent keys if needed
    }


__all__ = ["router"]
