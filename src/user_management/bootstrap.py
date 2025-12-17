"""Bootstrap for user management unifying user and auth services."""
from dataclasses import dataclass

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management.api.dependencies import (
    AuthDependencies,
    get_auth_dependencies,
)
from src.user_management.application import UserReadService, AuthService
from src.user_management.application.services.user_service import UserService
from src.user_management.config.settings import UserSettings, user_settings
from src.user_management.infrastructure.adapters.user_repository_adapter import (
    UserRepositoryAdapter,
)
from src.user_management.infrastructure.dependencies.providers import (
    get_password_hasher,
    get_token_provider,
)
from src.user_management.infrastructure.repositories.fake_user_repository import (
    FakeUserRepository,
)
from src.user_management.infrastructure.repositories.sqlalchemy_user_repository import (
    UserRepository,
)


@dataclass
class UserManagementModule:
    auth_service: AuthService
    auth_queries: UserReadService
    user_service: UserService
    settings: UserSettings


def build_user_management_module(
    session: AsyncSession, *, lightweight_mode: bool = False
) -> UserManagementModule:
    """Compose User and Auth services with a shared repository."""

    user_repo = FakeUserRepository() if lightweight_mode else UserRepository(db=session)
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
        auth_service=auth_service,
        auth_queries=auth_queries,
        user_service=user_service,
        settings=user_settings,
    )


def bind_user_management_module(app: FastAPI, module: UserManagementModule) -> None:
    """Wire dependency overrides for the user management module."""
    app.dependency_overrides[get_auth_dependencies] = lambda: AuthDependencies(
        user_service=module.user_service,
        auth_service=module.auth_service,
        auth_queries=module.auth_queries,
        settings=module.settings,
    )


__all__ = [
    "UserManagementModule",
    "bind_user_management_module",
    "build_user_management_module",
]
