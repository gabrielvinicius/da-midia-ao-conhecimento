from fastapi import FastAPI

from src.shared.infrastructure.observability.logging.logging_config import get_logger

logger = get_logger("validation")

def register_validation_middleware(app: FastAPI):
    # Example of custom logic if needed, otherwise FastAPI handles it.
    # This function was likely setting up handlers or custom middleware.
    pass
