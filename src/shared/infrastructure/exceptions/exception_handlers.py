"""Tradução única dos erros de aplicação para HTTP."""
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.shared.domain.errors import (
    AccessDeniedError,
    ConflictError,
    DomainError,
    NotFoundError,
    TemporarilyUnavailableError,
    ValidationError,
)
from src.shared.infrastructure.observability.logging.logging_config import get_logger

logger = get_logger("api.errors")

_STATUS = (
    (NotFoundError, status.HTTP_404_NOT_FOUND, "NOT_FOUND"),
    (AccessDeniedError, status.HTTP_403_FORBIDDEN, "ACCESS_DENIED"),
    (ConflictError, status.HTTP_409_CONFLICT, "CONFLICT"),
    (TemporarilyUnavailableError, status.HTTP_503_SERVICE_UNAVAILABLE, "UNAVAILABLE"),
    (ValidationError, 422, "VALIDATION_ERROR"),
    (DomainError, status.HTTP_400_BAD_REQUEST, "DOMAIN_ERROR"),
)


def _handler(status_code: int, code: str):
    async def handle(request: Request, exc: Exception):
        # "detail", como nas HTTPException do FastAPI, que a interface já lê.
        return JSONResponse(status_code=status_code, content={"detail": str(exc), "code": code})

    return handle


async def _unexpected(request: Request, exc: Exception):
    """Erro não previsto: registra com o rastro e responde sem expor detalhes internos."""
    logger.error(
        "api.unhandled_error",
        method=request.method,
        path=request.url.path,
        error=str(exc),
        exc_info=exc,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Erro interno do servidor", "code": "INTERNAL_ERROR"},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """O FastAPI escolhe o tratador da classe mais específica do erro."""
    for error_class, status_code, code in _STATUS:
        app.add_exception_handler(error_class, _handler(status_code, code))
    app.add_exception_handler(Exception, _unexpected)
