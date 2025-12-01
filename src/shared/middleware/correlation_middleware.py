import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = structlog.get_logger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """Middleware to ensure every request has a correlation ID."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Extract correlation ID from header or generate a new one
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        
        # Bind correlation ID to structlog context for this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

        # Pass the correlation ID to the response headers
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
