from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession
from src.user_management.config.settings import AuthSettings
from src.user_management.infrastructure.user_repository import UserRepository
from src.user_management.application.services import UserService


class UserManagementContainer(containers.DeclarativeContainer):
    db: providers.Provider[AsyncSession] = providers.Dependency()

    auth_settings = providers.Singleton(AuthSettings)

    user_repository = providers.Factory(
        UserRepository,
        db=db,
    )

    user_service = providers.Factory(
        UserService,
        user_repository=user_repository,
        settings=auth_settings,
    )
