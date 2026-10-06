"""Provider registry for user_management adapters (hashing, tokens)."""
from __future__ import annotations

from passlib.context import CryptContext

from src.user_management.application.ports import PasswordHasherPort, TokenProviderPort
from src.user_management.config.settings import user_settings
from datetime import timedelta
from uuid import uuid4

from jose import JWTError, jwt

from src.shared.domain.time.clock import utcnow


class PasslibPasswordHasher(PasswordHasherPort):
    """Password hasher constrained to bcrypt to avoid crypt()-related warnings.
    """

    def __init__(self) -> None:
        self._ctx = CryptContext(
            schemes=["bcrypt"],
            deprecated="auto",
        )

    # O bcrypt só considera os primeiros 72 bytes. O corte fica aqui, igual
    # no cadastro, na troca e na verificação; antes, o serviço cortava 72
    # caracteres só no cadastro, e senhas com acentos passavam do limite.
    @staticmethod
    def _bounded(password: str) -> bytes:
        return password.encode("utf-8")[:72]

    def hash(self, password: str) -> str:
        return self._ctx.hash(self._bounded(password))

    def verify(self, password: str, hashed: str) -> bool:
        return self._ctx.verify(self._bounded(password), hashed)


class JwtTokenProvider(TokenProviderPort):
    """Tokens JWT com o tipo no conteúdo: o de renovação não vale como acesso.

    O de renovação leva um id (jti) para poder ser revogado no logout.
    """

    @staticmethod
    def _encode(payload: dict, ttl_seconds: float) -> str:
        payload = {**payload, "exp": utcnow() + timedelta(seconds=ttl_seconds)}
        return jwt.encode(payload, user_settings.secret_key, algorithm=user_settings.algorithm)

    def create_access_token(self, user_id):
        return self._encode(
            {"sub": str(user_id), "type": "access"}, user_settings.access_token_expire_minutes * 60
        )

    def create_refresh_token(self, user_id):
        return self._encode(
            {"sub": str(user_id), "type": "refresh", "jti": uuid4().hex},
            user_settings.refresh_token_expire_minutes * 60,
        )

    def create_scoped_token(self, user_id, purpose, ttl_seconds, resource=None):
        payload = {"sub": str(user_id), "type": "scoped", "scope": str(purpose)}
        if resource is not None:
            payload["res"] = str(resource)
        return self._encode(payload, ttl_seconds)

    def verify_refresh_token(self, token: str) -> dict | None:
        payload = self.verify_token(token)
        return payload if payload and payload.get("type") == "refresh" else None

    def verify_token(self, token: str) -> dict | None:
        try:
            return jwt.decode(token, user_settings.secret_key, algorithms=[user_settings.algorithm])
        except JWTError:
            return None


def get_password_hasher() -> PasswordHasherPort:
    if user_settings.lightweight_mode:
        class _FakeHasher(PasswordHasherPort):
            def hash(self, password: str) -> str:
                return f"fake-{password}"

            def verify(self, password: str, hashed: str) -> bool:
                return hashed == f"fake-{password}"
        return _FakeHasher()
    return PasslibPasswordHasher()


def get_token_provider() -> TokenProviderPort:
    return JwtTokenProvider()


__all__ = [
    "get_password_hasher",
    "get_token_provider",
    "PasslibPasswordHasher",
    "JwtTokenProvider",
]
