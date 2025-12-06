"""Bootstrap for user management unifying user and auth services."""
from dataclasses import dataclass

from fastapi import FastAPI

from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.settings import Settings, settings
from src.user_management.api.dependencies import (
    AuthDependencies,
    get_auth_dependencies,
)
from src.user_management.application import AuthQueries, AuthService
from src.user_management.application.user_service import UserService
from src.user_management.infrastructure.user_repository import UserRepository


@dataclass
class UserManagementModule:
    auth_service: AuthService
    auth_queries: AuthQueries
    user_service: UserService
    settings: Settings


def build_user_management_module(session: AsyncSession) -> UserManagementModule:
    """Compose User and Auth services with a shared repository."""
    user_repo = UserRepository(db=session)
    # Use global settings
    user_service = UserService(user_repository=user_repo, settings=settings)
    auth_service = AuthService(user_service=user_service, settings=settings)
    auth_queries = AuthQueries(user_repository=user_repo)

    return UserManagementModule(
        auth_service=auth_service,
        auth_queries=auth_queries,
        user_service=user_service,
        settings=settings,
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