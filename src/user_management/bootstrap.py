"""Bootstrap for user management unifying user and auth services."""
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from src.auth.config.settings import AuthSettings

from src.auth.application.queries.auth_queries import AuthQueries
from src.auth.application.services.auth_service import AuthService
from src.auth.infrastructure.user_repository import UserRepository
from src.user_management.application.services import UserService


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
    auth_service = AuthService(user_repository=user_repo, settings=settings)
    auth_queries = AuthQueries(user_repository=user_repo)
    user_service = UserService(user_repository=user_repo)

    return UserManagementModule(
        auth_service=auth_service,
        auth_queries=auth_queries,
        user_service=user_service,
        settings=settings,
    )


__all__ = ["UserManagementModule", "build_user_management_module"]
