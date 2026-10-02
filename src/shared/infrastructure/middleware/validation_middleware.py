from __future__ import annotations

from typing import Any, Dict, List

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.responses import JSONResponse

from src.shared.infrastructure.observability.logging.logging_config import get_logger

logger = get_logger("validation")


def safe_errors(exc: RequestValidationError) -> List[Dict[str, Any]]:
    """Onde e por que a validação falhou, sem o valor recebido.

    O log gravava o corpo da requisição e o campo "input" de cada erro: um
    cadastro com e-mail inválido deixava a senha em texto puro nos logs.
    """
    return [
        {"loc": list(error.get("loc", ())), "type": error.get("type"), "msg": error.get("msg")}
        for error in exc.errors()
    ]


def register_validation_middleware(app: FastAPI) -> None:
    """Respostas 422 e log de validação sem dados enviados pelo usuário."""

    @app.exception_handler(RequestValidationError)
    async def request_validation_error_handler(  # type: ignore[override]
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = safe_errors(exc)
        logger.warning(
            "http.request.validation_failed",
            path=request.url.path,
            method=request.method,
            errors=errors,
        )
        return JSONResponse(status_code=422, content={"detail": errors})
