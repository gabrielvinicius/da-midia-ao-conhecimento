"""Composition root helpers for the auth module."""
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.container import AuthContainer
from src.auth.application.queries.auth_queries import AuthQueries
from src.auth.application.services.auth_service import AuthService
from src.auth.application.services.user_service import UserService
from src.auth.config.settings import AuthSettings


@dataclass
class AuthModule:
    """Structured dependencies exposed by the auth module."""

    auth_service: AuthService
    auth_queries: AuthQueries
    user_service: UserService
    settings: AuthSettings


def build_auth_module(session: AsyncSession) -> AuthModule:
    """Wire auth dependencies for a given database session."""

    container = AuthContainer(db=session)
    return AuthModule(
        auth_service=container.auth_service(),
        auth_queries=container.auth_queries(),
        user_service=container.user_service(),
        settings=container.auth_settings(),
    )
