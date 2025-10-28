# src/auth/application/services/user_service.py
"""User service responsible for orchestrating registration workflows."""

from typing import Dict, Any

import structlog

from src.auth.application.services.auth_service import AuthService

logger = structlog.get_logger(__name__)


class UserService:
    """High level user related application service."""

    def __init__(self, auth_service: AuthService) -> None:
        self._auth_service = auth_service

    async def register_user(self, email: str, password: str) -> Dict[str, Any]:
        """Register a new user delegating creation to :class:`AuthService`."""

        logger.info("user_service.register.started", email=email)
        user = await self._auth_service.create_user(email=email, password=password)
        logger.info("user_service.register.completed", user_id=str(user.id))

        return {
            "success": True,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role.value,
            },
        }
