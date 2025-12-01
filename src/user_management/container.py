from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.config.settings import Settings, settings
from src.user_management.application.auth_service import AuthService
from src.user_management.application.queries.auth_queries import AuthQueries
from src.user_management.application.user_service import UserService
from src.user_management.infrastructure.user_repository import UserRepository


class AuthContainer(containers.DeclarativeContainer):
    db: providers.Provider[AsyncSession] = providers.Dependency()

    # Use global settings singleton
    auth_settings = providers.Object(settings)

    user_repository = providers.Factory(
        UserRepository,
        db=db,
    )

    auth_queries = providers.Factory(
        AuthQueries,
        user_repository=user_repository,
    )

    user_service = providers.Factory(
        UserService,
        user_repository=user_repository,
        settings=auth_settings,
    )

    auth_service = providers.Factory(
        AuthService,
        user_service=user_service,
        settings=auth_settings,
    )