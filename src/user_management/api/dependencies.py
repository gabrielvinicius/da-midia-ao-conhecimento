# src/user_management/api/dependencies.py
from fastapi import Depends
from src.user_management.application.services import UserService
from src.user_management.bootstrap import get_user_service as get_user_service_from_bootstrap

# This is a simple pass-through for now, but allows for future flexibility
# if we need to add more complex dependency logic for the API layer.
def get_user_service() -> UserService:
    """
    FastAPI dependency provider for the UserService.
    """
    return get_user_service_from_bootstrap()

