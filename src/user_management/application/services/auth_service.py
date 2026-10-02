"""Login e renovação da sessão."""
from __future__ import annotations

from typing import Any

import structlog

from src.user_management.domain.errors import InvalidCredentialsError

from .user_service import UserService

logger = structlog.get_logger(__name__)


class AuthService:
    def __init__(self, user_service: UserService, settings: Any) -> None:
        self.user_service = user_service
        self.settings = settings

    async def authenticate_user(self, email: str, password: str) -> dict[str, Any]:
        logger.info("auth.authenticate.started", email=email)
        try:
            result = await self.user_service.authenticate_user(email, password)
        except InvalidCredentialsError as exc:
            logger.warning("auth.authenticate.failed", email=email, reason=str(exc) or "invalid_credentials")
            raise
        logger.info("auth.authenticate.success", email=email)
        return result

    async def refresh(self, refresh_token: str) -> dict[str, str]:
        """Novos tokens a partir do de renovação, só para usuário existente e ativo.

        Sem a consulta ao usuário, uma conta desativada ou excluída continuava
        renovando a sessão indefinidamente com o cookie que já tinha.
        """
        tokens = self.user_service.token_provider
        payload = tokens.verify_refresh_token(refresh_token)
        user_id = payload.get("sub") if payload else None
        user = await self.user_service.user_read_service.get_user_by_id(user_id) if user_id else None
        if user is None or not user.is_active:
            raise InvalidCredentialsError("Sessão inválida")
        return {
            "access_token": tokens.create_access_token(user.id),
            "refresh_token": tokens.create_refresh_token(user.id),
        }
