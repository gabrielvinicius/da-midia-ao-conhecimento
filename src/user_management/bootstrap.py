"""Bootstrap for user management unifying user and auth services."""
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from src.user_management.config.settings import AuthSettings

from src.user_management.infrastructure.user_repository import UserRepository
from src.user_management.application import AuthQueries, AuthService
from src.user_management.application.user_service import UserService


@dataclass
class UserManagementModule:
    auth_service: AuthService
    auth_queries: AuthQueries
    user_service: UserService
    settings: AuthSettings


def build_user_management_module(session: AsyncSession) -> UserManagementModule:
    """Compose User and Auth services with a shared repository."""

    user_repo = UserRepository(db=session)
    settings = AuthSettings()
    user_service = UserService(user_repository=user_repo, settings=settings)
    auth_service = AuthService(user_service=user_service, settings=settings)
    auth_queries = AuthQueries(user_repository=user_repo)

    return UserManagementModule(
        auth_service=auth_service,
        auth_queries=auth_queries,
        user_service=user_service,
        settings=settings,
    )


__all__ = ["UserManagementModule", "build_user_management_module"]
