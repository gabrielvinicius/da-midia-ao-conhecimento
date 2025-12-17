import time

from fastapi import FastAPI, Request

from src.shared.infrastructure.observability.logging.logging_config import get_logger

logger = get_logger("performance")

def register_performance_middleware(app: FastAPI):
    @app.middleware("http")
    async def add_process_time_header(request: Request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        logger.info("Request processed", duration=process_time, path=request.url.path)
        return response
