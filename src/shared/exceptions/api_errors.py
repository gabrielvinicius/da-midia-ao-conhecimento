# src/shared/exceptions/api_errors.py
"""Handlers globais para tratamento de exceções na API.
Converte exceções de domínio em respostas HTTP apropriadas.
"""

import traceback

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.shared.infrastructure.logging import get_logger

from src.shared.domain.errors import (
    AuthenticationError,
    AuthorizationError,
    BusinessRuleViolationError,
    ConfigurationError,
    DomainException,
    ExternalServiceError,
    MediaNotFoundError,
    MediaProcessingError,
    RateLimitExceededError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    StorageError,
    UnsupportedMediaTypeError,
    ValidationError,
)

logger = get_logger("api_errors")


# Mapeamento de exceções para códigos HTTP
EXCEPTION_STATUS_MAPPING = {
    ValidationError: 400,
    BusinessRuleViolationError: 400,
    ResourceNotFoundError: 404, # Changed
    ResourceAlreadyExistsError: 409,
    AuthenticationError: 401,
    AuthorizationError: 403,
    MediaProcessingError: 422,
    UnsupportedMediaTypeError: 415,
    ExternalServiceError: 502,
    ConfigurationError: 500,
    RateLimitExceededError: 429,
    StorageError: 500,
}


async def domain_exception_handler(request: Request, exc: DomainException) -> JSONResponse:
    """Handler para exceções de domínio."""
    # Determinar status code baseado no tipo da exceção
    status_code = EXCEPTION_STATUS_MAPPING.get(type(exc), 500)

    # Log da exceção
    logger.warning(
        "Domain exception occurred",
        exception_type=type(exc).__name__,
        error_code=getattr(exc, "error_code", None),
        message=getattr(exc, "message", str(exc)),
        details=getattr(exc, "details", {}),
        status_code=status_code,
        path=str(request.url)
    )

    return JSONResponse(
        status_code=status_code,
        content={
            "error": getattr(exc, "error_code", type(exc).__name__),
            "message": getattr(exc, "message", str(exc)),
            "details": getattr(exc, "details", {}),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handler para HTTPException do FastAPI."""
    logger.warning(
        "HTTP exception occurred",
        status_code=exc.status_code,
        detail=exc.detail,
        path=str(request.url)
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "details": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handler para exceções não tratadas."""
    # Log completo da exceção
    logger.error(
        "Unhandled exception occurred",
        exception_type=type(exc).__name__,
        message=str(exc),
        traceback=traceback.format_exc(),
        path=str(request.url)
    )

    # Em produção, não expor detalhes internos
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "An internal server error occurred",
            "details": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


class ExceptionLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware para capturar e logar todas as exceções."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            logger.error(
                "Exception caught by middleware",
                exception_type=type(exc).__name__,
                message=str(exc),
                method=request.method,
                url=str(request.url),
                traceback=traceback.format_exc()
            )
            raise


def register_exception_handlers(app):
    """Registra todos os handlers de exceção na aplicação FastAPI."""
    # Handlers específicos (ordem importa - mais específicos primeiro)
    app.add_exception_handler(DomainException, domain_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    # Middleware para logging
    app.add_middleware(ExceptionLoggingMiddleware)

    logger.info("Exception handlers registered successfully")


# Funções utilitárias para lançar exceções comuns

def raise_not_found(resource_type: str, resource_id: str) -> None:
    """Utilitário para lançar erro de recurso não encontrado."""
    raise ResourceNotFoundError(resource_type, resource_id)


def raise_validation_error(field: str, value, reason: str) -> None:
    """Utilitário para lançar erro de validação."""
    raise ValidationError(field, value, reason)


def raise_unauthorized(action: str, resource: str = None) -> None:
    """Utilitário para lançar erro de autorização."""
    raise AuthorizationError(action, resource)


def raise_business_rule_violation(rule: str, context: dict = None) -> None:
    """Utilitário para lançar violação de regra de negócio."""
    raise BusinessRuleViolationError(rule, context)
