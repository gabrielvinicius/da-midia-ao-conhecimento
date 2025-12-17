from fastapi import Request
from fastapi.responses import JSONResponse

from src.shared.infrastructure.observability.logging.logging_config import get_logger

logger = get_logger("error_middleware")

async def unified_error_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:
        logger.error("Unhandled exception", error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error", "message": str(exc)}
        )
