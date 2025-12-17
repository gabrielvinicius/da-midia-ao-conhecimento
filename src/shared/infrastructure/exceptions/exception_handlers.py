from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.shared.domain.errors import (
    DomainError,
    ValidationError,
    ResourceNotFoundError,
)


def register_exception_handlers(app: FastAPI) -> None:
    """Registers global exception handlers."""

    @app.exception_handler(DomainError)
    async def domain_exception_handler(request: Request, exc: DomainError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": str(exc), "code": "DOMAIN_ERROR"},
        )

    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(
        request: Request, exc: ResourceNotFoundError
    ):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": str(exc), "code": "NOT_FOUND"},
        )

    @app.exception_handler(ValidationError)
    async def validation_exception_handler(
        request: Request, exc: ValidationError
    ):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": str(exc),
                "details": getattr(exc, "args", ()),
                "code": "VALIDATION_ERROR",
            },
        )
