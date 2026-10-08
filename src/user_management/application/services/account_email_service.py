"""Confirmação de e-mail no cadastro e recuperação de senha por e-mail.

O envio de e-mails é opcional (EmailSenderPort.enabled). Desligado, o
cadastro entra direto, como antes, e a recuperação de senha não está
disponível. Ligado, a conta só entra depois de confirmar o e-mail.

Os links levam tokens de finalidade restrita e curta duração. O de nova
senha carrega uma marca do hash da senha atual: deixa de valer assim que a
senha muda, ou seja, serve uma única vez. O de confirmação carrega o e-mail:
não serve para outro endereço.
"""
from __future__ import annotations

import hashlib
from typing import Any, Optional

import structlog

from src.shared.application.privacy import masked_email
from src.user_management.application.dtos import CreateUserCommand
from src.user_management.application.ports import EmailSenderPort, LoginAttemptLimiterPort
from src.user_management.application.tokens import TokenPurpose
from src.user_management.domain import User
from src.user_management.domain.errors import InvalidLinkError
from src.user_management.domain.rules import normalize_email

from .user_service import UserService

logger = structlog.get_logger(__name__)

# Pedidos de e-mail por endereço (cadastro reenviado, nova senha) numa hora.
MAX_EMAILS_PER_HOUR = 3


def password_fingerprint(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:16]


class AccountEmailService:
    def __init__(
        self,
        user_service: UserService,
        sender: EmailSenderPort,
        settings: Any,
        limiter: Optional[LoginAttemptLimiterPort] = None,
    ) -> None:
        self._users = user_service
        self._sender = sender
        self._settings = settings
        self._limiter = limiter

    @property
    def enabled(self) -> bool:
        return bool(self._sender.enabled)

    @property
    def _tokens(self):
        return self._users.token_provider

    async def register(self, command: CreateUserCommand) -> tuple[User, bool]:
        """Cria a conta; com e-mail ligado, ela fica à espera da confirmação.
        Devolve a conta e se a confirmação é necessária."""
        user = await self._users.create_user(command, email_verified=not self.enabled)
        if self.enabled:
            await self._send_verification(user)
        return user, self.enabled

    async def confirm_email(self, token: str) -> None:
        payload = self._payload(token, TokenPurpose.EMAIL_VERIFICATION)
        user = await self._user(payload)
        if user.email != payload.get("res"):
            raise InvalidLinkError()
        if not user.email_verified:
            user.confirm_email()
            await self._users.user_repository.save(user)
        logger.info("auth.email_confirmed", email=masked_email(user.email))

    async def resend_verification(self, email: str) -> None:
        """Sempre responde igual: não revela se existe conta com o e-mail."""
        user = await self._requestable(email)
        if user and not user.email_verified:
            await self._send_verification(user)

    async def request_password_reset(self, email: str) -> None:
        """Sempre responde igual: não revela se existe conta com o e-mail."""
        user = await self._requestable(email)
        if user and user.is_active:
            token = self._tokens.create_scoped_token(
                user.id,
                TokenPurpose.PASSWORD_RESET.value,
                self._settings.password_reset_minutes * 60,
                password_fingerprint(user.password_hash),
            )
            await self._send(
                user,
                "Redefinir a senha",
                "Recebemos um pedido para redefinir a senha da sua conta no Síntese.\n\n"
                f"Para escolher uma nova senha, abra o link abaixo (vale por {self._settings.password_reset_minutes} minutos "
                f"e uma única vez):\n\n{self._link('redefinir-senha', token)}\n\n"
                "Se você não pediu, ignore este e-mail: a senha atual continua valendo.",
            )

    async def reset_password(self, token: str, new_password: str) -> None:
        payload = self._payload(token, TokenPurpose.PASSWORD_RESET)
        user = await self._user(payload)
        if payload.get("res") != password_fingerprint(user.password_hash):
            raise InvalidLinkError()  # a senha já mudou: o link foi usado
        self._users._validate_password_strength(new_password)
        user.change_password_hash(self._users.password_hasher.hash(new_password))
        user.confirm_email()  # quem recebeu o link é dono do e-mail
        await self._users.user_repository.save(user)
        logger.info("auth.password_reset", email=masked_email(user.email))

    # --- auxiliares

    async def _send_verification(self, user: User) -> None:
        token = self._tokens.create_scoped_token(
            user.id,
            TokenPurpose.EMAIL_VERIFICATION.value,
            self._settings.email_verification_hours * 3600,
            user.email,
        )
        await self._send(
            user,
            "Confirme seu e-mail",
            "Sua conta no Síntese foi criada.\n\n"
            f"Para ativá-la, confirme o e-mail pelo link abaixo (vale por {self._settings.email_verification_hours} horas):"
            f"\n\n{self._link('confirmar-email', token)}\n\n"
            "Se você não criou esta conta, ignore este e-mail.",
        )

    async def _send(self, user: User, subject: str, body: str) -> None:
        # Uma falha de envio não desfaz o cadastro: o link pode ser pedido de novo.
        try:
            await self._sender.send(user.email, subject, body)
            logger.info("auth.email_sent", subject=subject, email=masked_email(user.email))
        except Exception as exc:
            logger.error("auth.email_failed", subject=subject, email=masked_email(user.email), error=str(exc))

    async def _requestable(self, email: str) -> Optional[User]:
        """A conta do e-mail, se o envio está ligado e o limite por hora permite."""
        if not self.enabled:
            return None
        # Prefixo próprio: "email:" é a chave do limite de login, e um pedido
        # de nova senha não pode bloquear o login da pessoa.
        key = f"account-mail:{normalize_email(email)}"
        if self._limiter:
            if await self._limiter.retry_after(key) > 0:
                return None
            await self._limiter.register_failure(key, MAX_EMAILS_PER_HOUR, 3600)
        return await self._users.user_read_service.get_user_by_email(normalize_email(email))

    def _payload(self, token: str, purpose: TokenPurpose) -> dict:
        payload = self._tokens.verify_token(token) if token else None
        if not payload or payload.get("type") != "scoped" or payload.get("scope") != purpose.value:
            raise InvalidLinkError()
        return payload

    async def _user(self, payload: dict) -> User:
        from uuid import UUID

        try:
            user = await self._users.user_read_service.get_user_by_id(UUID(str(payload.get("sub"))))
        except ValueError:
            user = None
        if user is None:
            raise InvalidLinkError()
        return user

    def _link(self, page: str, token: str) -> str:
        return f"{self._settings.public_url.rstrip('/')}/{page}?token={token}"


__all__ = ["AccountEmailService", "MAX_EMAILS_PER_HOUR", "password_fingerprint"]
