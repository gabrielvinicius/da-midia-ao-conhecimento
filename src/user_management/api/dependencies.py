# src/auth/api/dependencies.py
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from src.user_management.config.settings import AuthSettings

from src.user_management.application.queries.auth_queries import AuthQueries
from src.user_management.application.services.auth_service import AuthService
from src.user_management.application.user_service import UserService


class AuthDependenciesNotConfigured(RuntimeError):
    """Raised when the dependency provider has not been registered."""


@dataclass(frozen=True)
class AuthDependencies:
    """Aggregates the collaborators required by the auth API."""

    user_service: UserService
    auth_service: AuthService
    auth_queries: AuthQueries
    settings: AuthSettings


def get_auth_dependencies() -> AuthDependencies:
    """Base provider to be overridden during application startup."""

    raise AuthDependenciesNotConfigured(
        "Auth dependencies are not configured. Register providers in the lifespan handler."
    )


AuthDeps = Annotated[AuthDependencies, Depends(get_auth_dependencies)]


def get_user_service(deps: AuthDeps) -> UserService:
    return deps.user_service


def get_auth_service(deps: AuthDeps) -> AuthService:
    return deps.auth_service


def get_auth_queries(deps: AuthDeps) -> AuthQueries:
    return deps.auth_queries


def get_auth_settings(deps: AuthDeps) -> AuthSettings:
    return deps.settings


__all__ = [
    "AuthDependencies",
    "AuthDependenciesNotConfigured",
    "get_auth_dependencies",
    "get_auth_queries",
    "get_auth_service",
    "get_auth_settings",
    "get_user_service",
]
