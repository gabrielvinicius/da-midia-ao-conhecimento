from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession
from src.user_management.config.settings import AuthSettings

from src.user_management.application.queries.auth_queries import AuthQueries
from src.user_management.application.services.auth_service import AuthService
from src.user_management.infrastructure.user_repository import UserRepository
from src.user_management.application.services import UserService


class AuthContainer(containers.DeclarativeContainer):
    db: providers.Provider[AsyncSession] = providers.Dependency()

    auth_settings = providers.Singleton(AuthSettings)

    user_repository = providers.Factory(
        UserRepository,
        db=db,
    )

    auth_queries = providers.Factory(
        AuthQueries,
        user_repository=user_repository,
    )

    auth_service = providers.Factory(
        AuthService,
        user_repository=user_repository,
        settings=auth_settings,
    )

    user_service = providers.Factory(
        UserService,
        user_repository=user_repository,
    )
