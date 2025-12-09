from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from src.shared.domain.errors import DomainException, ResourceNotFoundException, DomainValidationError

def register_exception_handlers(app: FastAPI) -> None:
    """Registers global exception handlers."""

    @app.exception_handler(DomainException)
    async def domain_exception_handler(request: Request, exc: DomainException):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": exc.message, "code": "DOMAIN_ERROR"},
        )

    @app.exception_handler(ResourceNotFoundException)
    async def resource_not_found_handler(request: Request, exc: ResourceNotFoundException):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"error": exc.message, "code": "NOT_FOUND"},
        )

    @app.exception_handler(DomainValidationError)
    async def validation_exception_handler(request: Request, exc: DomainValidationError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": exc.message, "details": exc.details, "code": "VALIDATION_ERROR"},
        )
