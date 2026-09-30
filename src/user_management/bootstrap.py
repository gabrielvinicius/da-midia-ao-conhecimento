"""Bootstrap for the User Management module."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Tuple

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management.api.dependencies import (
    get_auth_queries,
    get_auth_service,
    get_auth_settings,
    get_login_throttle,
    get_user_service,
)
from src.user_management.application.auth_queries import UserReadService
from src.user_management.application.services.auth_service import AuthService
from src.user_management.application.services.login_throttle import LoginThrottle
from src.user_management.application.services.user_service import UserService
from src.user_management.config.settings import user_settings
from src.user_management.infrastructure.adapters.user_repository_adapter import (
    UserRepositoryAdapter,
)
from src.user_management.infrastructure.dependencies.providers import (
    get_password_hasher,
    get_token_provider,
)
from src.user_management.infrastructure.repositories.sqlalchemy_user_repository import (
    UserRepository,
)


@dataclass
class UserManagementModule:
    """Public surface used by the user management API and other modules."""

    user_service: UserService
    auth_service: AuthService
    auth_queries: UserReadService


def build_user_management_components(
    session: AsyncSession,
) -> UserManagementModule:
    """Compose the user management module with all its dependencies."""
    user_repo = UserRepository(db=session)
    user_repo_adapter = UserRepositoryAdapter(user_repo)
    auth_queries = UserReadService(user_repository=user_repo_adapter)

    user_service = UserService(
        user_repository=user_repo_adapter,
        user_read_service=auth_queries,
        password_hasher=get_password_hasher(),
        token_provider=get_token_provider(),
        settings=user_settings,
    )

    auth_service = AuthService(user_service=user_service, settings=user_settings)

    return UserManagementModule(
        user_service=user_service,
        auth_service=auth_service,
        auth_queries=auth_queries,
    )


def bind_user_management_module(app: FastAPI, module: UserManagementModule) -> None:
    """Register dependency overrides for user management use cases."""
    app.dependency_overrides[get_user_service] = lambda: module.user_service
    app.dependency_overrides[get_auth_service] = lambda: module.auth_service
    app.dependency_overrides[get_auth_queries] = lambda: module.auth_queries
    app.dependency_overrides[get_auth_settings] = lambda: user_settings
    login_throttle = _build_login_throttle()
    app.dependency_overrides[get_login_throttle] = lambda: login_throttle


def _build_login_throttle() -> LoginThrottle:
    """Limitador de login com Redis, compartilhado entre os processos da API."""
    from src.shared.infrastructure.config.settings import settings as shared_settings
    from src.user_management.infrastructure.adapters.security.login_attempt_limiter import (
        build_login_attempt_limiter,
    )

    redis_url = None if os.getenv("LIGHTWEIGHT_BOOTSTRAP") == "1" else shared_settings.redis_url
    return LoginThrottle(
        build_login_attempt_limiter(redis_url),
        user_settings.login_max_attempts_per_email,
        user_settings.login_max_attempts_per_ip,
        user_settings.login_block_seconds,
    )


__all__ = [
    "UserManagementModule",
    "build_user_management_components",
    "bind_user_management_module",
]