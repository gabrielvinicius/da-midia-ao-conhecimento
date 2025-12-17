from fastapi import APIRouter

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/ping")
async def ping() -> dict:
    return {"status": "ok"}


__all__ = ["router"]
