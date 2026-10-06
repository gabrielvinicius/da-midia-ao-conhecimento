"""Login, renovação e encerramento da sessão, e a verificação de cada token.

A verificação ficava copiada em três dependências da API (cabeçalho, URL do
vídeo e WebSocket), com o mesmo decode e a mesma consulta ao usuário; e
nenhuma conferia o tipo, então o token de renovação (7 dias) valia como token
de acesso. Agora há um só lugar, que confere a finalidade do token.
"""
from __future__ import annotations

import time
from typing import Any, Optional
from uuid import UUID

import structlog

from src.shared.application.privacy import masked_email
from src.user_management.application.ports import RevokedTokensPort
from src.user_management.application.tokens import SCOPED_PURPOSES, TokenPurpose
from src.user_management.domain import User
from src.user_management.domain.errors import InvalidCredentialsError

from .user_service import UserService

logger = structlog.get_logger(__name__)


class AuthService:
    def __init__(
        self,
        user_service: UserService,
        settings: Any,
        revoked_tokens: Optional[RevokedTokensPort] = None,
    ) -> None:
        self.user_service = user_service
        self.settings = settings
        self._revoked = revoked_tokens

    @property
    def _tokens(self):
        return self.user_service.token_provider

    async def authenticate_user(self, email: str, password: str) -> dict[str, Any]:
        logger.info("auth.authenticate.started", email=masked_email(email))
        try:
            result = await self.user_service.authenticate_user(email, password)
        except InvalidCredentialsError as exc:
            logger.warning("auth.authenticate.failed", email=masked_email(email), reason=str(exc) or "invalid_credentials")
            raise
        logger.info("auth.authenticate.success", email=masked_email(email))
        return result

    async def user_for_token(
        self, token: Optional[str], purpose: TokenPurpose = TokenPurpose.ACCESS, resource: Any = None
    ) -> User:
        """Usuário ativo dono de um token válido para ``purpose`` (e ``resource``)."""
        payload = self._tokens.verify_token(token) if token else None
        if not payload or not self._serves(payload, purpose, resource):
            raise InvalidCredentialsError("Sessão inválida ou expirada")
        return await self._active_user(payload.get("sub"))

    @staticmethod
    def _serves(payload: dict, purpose: TokenPurpose, resource: Any) -> bool:
        # Tokens emitidos antes do campo "type" eram sempre de acesso.
        kind = payload.get("type", TokenPurpose.ACCESS.value)
        if purpose in SCOPED_PURPOSES:
            return (
                kind == "scoped"
                and payload.get("scope") == purpose.value
                and (resource is None or payload.get("res") == str(resource))
            )
        return kind == purpose.value

    def issue_scoped_token(self, user: User, purpose: TokenPurpose, resource: Any = None) -> dict[str, Any]:
        """Token só para reproduzir uma mídia ou abrir o WebSocket de avisos."""
        if purpose not in SCOPED_PURPOSES:
            raise ValueError(f"Finalidade sem token próprio: {purpose}")
        ttl = (
            self.settings.stream_token_expire_minutes * 60
            if purpose == TokenPurpose.MEDIA_STREAM
            else self.settings.socket_token_expire_seconds
        )
        token = self._tokens.create_scoped_token(user.id, purpose.value, ttl, resource)
        return {"token": token, "expires_in": ttl}

    async def refresh(self, refresh_token: str) -> dict[str, str]:
        """Novos tokens a partir do de renovação, só para usuário existente e ativo.

        O token usado é revogado (rotação): copiado, ele só serve uma vez.
        """
        payload = await self._valid_refresh(refresh_token)
        user = await self._active_user(payload.get("sub"))
        await self._revoke(payload)
        return {
            "access_token": self._tokens.create_access_token(user.id),
            "refresh_token": self._tokens.create_refresh_token(user.id),
        }

    async def logout(self, refresh_token: Optional[str]) -> None:
        """Revoga o token de renovação. Antes, o logout só apagava o cookie, e
        uma cópia do token continuava renovando a sessão por 7 dias."""
        payload = self._tokens.verify_refresh_token(refresh_token) if refresh_token else None
        if payload:
            await self._revoke(payload)

    async def _valid_refresh(self, refresh_token: str) -> dict:
        payload = self._tokens.verify_refresh_token(refresh_token)
        jti = payload.get("jti") if payload else None
        if payload is None or (jti and self._revoked and await self._revoked.is_revoked(jti)):
            raise InvalidCredentialsError("Sessão inválida")
        return payload

    async def _revoke(self, payload: dict) -> None:
        jti = payload.get("jti")
        if jti and self._revoked:
            await self._revoked.revoke(jti, int(payload.get("exp", time.time()) - time.time()))

    async def _active_user(self, user_id: Optional[str]) -> User:
        """Conta excluída ou desativada perde o acesso já na próxima requisição."""
        try:
            key = UUID(str(user_id)) if user_id else None
        except ValueError:
            key = None
        user = await self.user_service.user_read_service.get_user_by_id(key) if key else None
        if user is None or not user.is_active:
            raise InvalidCredentialsError("Sessão inválida")
        return user
