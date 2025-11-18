"""Validation middleware registration for FastAPI applications."""

from __future__ import annotations

from typing import Iterable, List, Optional, Sequence

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware

from src.shared.infrastructure.logging_config import get_logger
from src.shared.validation.schemas import create_validation_error_response

logger = get_logger("validation_middleware")


class ContentValidationMiddleware(BaseHTTPMiddleware):
    """Basic request validation middleware.

    Ensures that request payloads obey the expected size constraints and that
    only supported content types are accepted for write operations. Responses
    follow the project-wide validation error schema to keep clients aligned
    with the documented contract.
    """

    def __init__(
        self,
        app,
        *,
        allowed_content_types: Optional[Iterable[str]] = None,
        max_body_size: int = 600 * 1024 * 1024,
    ) -> None:
        super().__init__(app)
        default_content_types = {
            "application/json",
            "multipart/form-data",
            "application/x-www-form-urlencoded",
            "text/plain",  # support raw text uploads (e.g., .txt summaries)
        }
        if allowed_content_types:
            default_content_types.update(allowed_content_types)
        self.allowed_content_types = default_content_types
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        if request.method in {"POST", "PUT", "PATCH"}:
            content_length_header = request.headers.get("content-length")
            if content_length_header:
                try:
                    content_length = int(content_length_header)
                except ValueError:
                    content_length = None
                else:
                    if content_length > self.max_body_size:
                        logger.warning(
                            "request_body_too_large",
                            method=request.method,
                            path=str(request.url),
                            content_length=content_length,
                        )
                        return self._build_response(
                            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            [
                                {
                                    "loc": ["body"],
                                    "msg": "Payload exceeds the allowed size",
                                    "type": "request_too_large",
                                }
                            ],
                        )

            content_type_header = request.headers.get("content-type", "")
            content_type = content_type_header.split(";")[0].strip()
            if content_type and content_type not in self.allowed_content_types:
                logger.warning(
                    "unsupported_content_type",
                    method=request.method,
                    path=str(request.url),
                    content_type=content_type,
                )
                return self._build_response(
                    status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    [
                        {
                            "loc": ["body"],
                            "msg": f"Unsupported content type: {content_type}",
                            "type": "invalid_content_type",
                        }
                    ],
                )

        return await call_next(request)

    @staticmethod
    def _build_response(status_code: int, validation_errors: Sequence[dict]) -> JSONResponse:
        error_response = create_validation_error_response(list(validation_errors))
        payload = error_response.model_dump(mode="json")
        return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


from fastapi.encoders import jsonable_encoder

def _build_validation_response(errors: list[dict], status_code: int) -> JSONResponse:
    response_data = {"detail": errors}
    return JSONResponse(status_code=status_code, content=jsonable_encoder(response_data))


async def _handle_request_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    request.state.validation_errors = errors  # type: ignore[attr-defined]
    logger.warning(
        "request_validation_error",
        path=str(request.url),
        method=request.method,
        errors=errors,
    )
    return _build_validation_response(errors, status.HTTP_422_UNPROCESSABLE_ENTITY)


async def _handle_pydantic_validation_error(
    request: Request, exc: PydanticValidationError
) -> JSONResponse:
    errors = exc.errors()
    logger.warning(
        "pydantic_validation_error",
        path=str(request.url),
        method=request.method,
        errors=errors,
    )
    return _build_validation_response(errors, status.HTTP_422_UNPROCESSABLE_ENTITY)


def register_validation_middleware(app: FastAPI) -> None:
    """Register validation middlewares and error hooks once per app."""
    if getattr(app.state, "validation_middleware_registered", False):
        return

    app.add_exception_handler(RequestValidationError, _handle_request_validation_error)
    app.add_exception_handler(PydanticValidationError, _handle_pydantic_validation_error)
    app.add_middleware(ContentValidationMiddleware)

    app.state.validation_middleware_registered = True
    logger.info("validation_middleware_registered")


__all__ = [
    "ContentValidationMiddleware",
    "register_validation_middleware",
]
