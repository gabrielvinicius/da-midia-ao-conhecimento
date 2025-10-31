"""Composition root for the user_management module."""
from sqlalchemy.ext.asyncio import AsyncSession
from src.user_management.application.services import UserService
from src.user_management.container import UserManagementContainer

_container: UserManagementContainer | None = None


def _get_container(session: AsyncSession) -> UserManagementContainer:
    """
    Singleton factory for the dependency injection container.
    """
    global _container
    if _container is None:
        _container = UserManagementContainer(db=session)
    return _container


def get_user_service(session: AsyncSession) -> UserService:
    """
    Builds and returns a UserService instance for a given database session.
    """
    container = _get_container(session)
    return container.user_service()
