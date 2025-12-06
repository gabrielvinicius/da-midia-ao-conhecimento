from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from src.shared.infrastructure.logging import get_logger

logger = get_logger("validation")

def register_validation_middleware(app: FastAPI):
    # Example of custom logic if needed, otherwise FastAPI handles it.
    # This function was likely setting up handlers or custom middleware.
    pass
