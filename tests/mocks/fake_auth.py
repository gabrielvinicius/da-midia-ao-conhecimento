"""Serviços e adapters fakes para autenticação/usuários em testes lightweight."""
from __future__ import annotations

import hashlib
from typing import Optional
from uuid import UUID

from src.user_management.application.auth_queries import UserReadService
from src.user_management.application.dtos import CreateUserCommand
from src.user_management.application.services.auth_service import AuthService
from src.user_management.application.services.user_service import UserService
from src.user_management.application.ports import PasswordHasherPort, TokenProviderPort
from src.user_management.config.settings import user_settings
from src.user_management.domain.entities.user import User, UserRole
from src.user_management.infrastructure.repositories.fake_user_repository import (
    FakeUserRepository,
)
from datetime import timedelta
import jwt
from src.shared.domain.time.clock import utcnow


class FakePasswordHasher(PasswordHasherPort):
    """Hasher simples baseado em SHA256, apenas para testes."""

    def hash(self, password: str) -> str:
        return hashlib.sha256(password.encode()).hexdigest()

    def verify(self, password: str, hashed: str) -> bool:
        return self.hash(password) == hashed


class FakeTokenProvider(TokenProviderPort):
    def create_access_token(self, user_id: UUID | str):
        expire = utcnow() + timedelta(
            minutes=user_settings.access_token_expire_minutes
        )
        payload = {"sub": str(user_id), "exp": expire}
        return jwt.encode(
            payload,
            user_settings.secret_key,
            algorithm=user_settings.algorithm,
        )

    def verify_token(self, token: str) -> dict | None:
        try:
            return jwt.decode(
                token,
                user_settings.secret_key,
                algorithms=[user_settings.algorithm],
            )
        except Exception:
            return None


def build_fake_auth() -> tuple[AuthService, UserService, UserReadService, FakeUserRepository]:
    repo = FakeUserRepository()
    password_hasher = FakePasswordHasher()
    token_provider = FakeTokenProvider()
    user_service = UserService(
        user_repository=repo,
        user_read_service=repo,
        password_hasher=password_hasher,
        token_provider=token_provider,
        settings=user_settings,
    )
    auth_service = AuthService(user_service=user_service, settings=user_settings)
    auth_queries = UserReadService(user_repository=repo)
    return auth_service, user_service, auth_queries, repo


async def seed_default_user(
    user_service: UserService, email: str, password: str, role: Optional[UserRole] = None
) -> User:
    role = role or UserRole.USER
    cmd = CreateUserCommand(email=email, password=password, role=role)
    result = await user_service.register_user(cmd)
    user_id = UUID(result["user"]["id"])
    user = await user_service.user_read_service.get_user_by_id(user_id)
    return user


__all__ = [
    "FakePasswordHasher",
    "FakeTokenProvider",
    "build_fake_auth",
    "seed_default_user",
]
