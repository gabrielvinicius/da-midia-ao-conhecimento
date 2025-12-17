import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.shared.infrastructure.observability.logging.logging_config import get_logger

logger = get_logger("correlation")

class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        # Contextvars could be used here
        logger.info(
            "Request started",
            correlation_id=correlation_id,
            path=request.url.path,
        )
        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id
        return response
