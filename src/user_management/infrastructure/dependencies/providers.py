"""Adaptadores de senha (bcrypt) e de tokens (JWT) do módulo de usuários."""
from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import bcrypt
import jwt

from src.shared.domain.time.clock import utcnow
from src.user_management.application.ports import PasswordHasherPort, TokenProviderPort
from src.user_management.config.settings import user_settings


class BcryptPasswordHasher(PasswordHasherPort):
    """Senhas com bcrypt, direto pela biblioteca.

    Antes, o passlib (sem versão nova desde 2020) intermediava e obrigava a
    manter o bcrypt abaixo da versão 4. Os hashes têm o mesmo formato
    ($2b$): as senhas já gravadas continuam valendo.
    """

    # O bcrypt só considera os primeiros 72 bytes. O corte fica aqui, igual
    # no cadastro, na troca e na verificação; antes, o serviço cortava 72
    # caracteres só no cadastro, e senhas com acentos passavam do limite.
    @staticmethod
    def _bounded(password: str) -> bytes:
        return password.encode("utf-8")[:72]

    def hash(self, password: str) -> str:
        return bcrypt.hashpw(self._bounded(password), bcrypt.gensalt()).decode("ascii")

    def verify(self, password: str, hashed: str) -> bool:
        try:
            return bcrypt.checkpw(self._bounded(password), hashed.encode("ascii"))
        except ValueError:  # hash malformado: nenhuma senha confere
            return False


class JwtTokenProvider(TokenProviderPort):
    """Tokens JWT (PyJWT) com o tipo no conteúdo: o de renovação não vale
    como acesso. O de renovação leva um id (jti) para poder ser revogado no
    logout. Antes, com python-jose, de manutenção irregular."""

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
        except jwt.PyJWTError:
            return None


def get_password_hasher() -> PasswordHasherPort:
    if user_settings.lightweight_mode:
        class _FakeHasher(PasswordHasherPort):
            def hash(self, password: str) -> str:
                return f"fake-{password}"

            def verify(self, password: str, hashed: str) -> bool:
                return hashed == f"fake-{password}"
        return _FakeHasher()
    return BcryptPasswordHasher()


def get_token_provider() -> TokenProviderPort:
    return JwtTokenProvider()


__all__ = [
    "get_password_hasher",
    "get_token_provider",
    "BcryptPasswordHasher",
    "JwtTokenProvider",
]
