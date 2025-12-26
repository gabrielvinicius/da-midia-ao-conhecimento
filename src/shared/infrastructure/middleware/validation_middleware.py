from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from src.shared.infrastructure.observability.logging.logging_config import get_logger

logger = get_logger("validation")

def _safe_validation_payload(exc: RequestValidationError) -> Dict[str, Any]:
    return {
        "errors": exc.errors(),
        "body": exc.body if isinstance(exc.body, (dict, list, str, int, float)) else None,
    }


def register_validation_middleware(app: FastAPI) -> None:
    """Registra handlers de validação com log estruturado.

    O FastAPI já devolve 422 automaticamente, mas sem padronizar logging/telemetria.
    Aqui centralizamos o log para facilitar troubleshooting (sem acoplar domínio).
    """

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(  # type: ignore[override]
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        logger.warning(
            "http.request.validation_failed",
            extra={
                "path": request.url.path,
                "method": request.method,
                **_safe_validation_payload(exc),
            },
        )
        return JSONResponse(status_code=422, content={"detail": exc.errors()})
