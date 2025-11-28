"""Uniform error handling middleware returning BaseResponseSchema."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from src.shared.api.unified_schemas import create_error_response


async def unified_error_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:  # pragma: no cover - catch-all
        # Later we can enrich with correlation_id if present in headers/context
        err = create_error_response(
            error=str(exc),
            message="Internal server error",
        )
        return JSONResponse(
            status_code=500,
            content=err.model_dump(),
        )


__all__ = ["unified_error_middleware"]
