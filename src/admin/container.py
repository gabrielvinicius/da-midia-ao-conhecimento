from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.application.queries.admin_queries import AdminQueries
from src.media_management.application.queries.media_queries import MediaQueries

class AdminContainer(containers.DeclarativeContainer):
    db: providers.Provider[AsyncSession] = providers.Dependency()
    media_queries: providers.Provider[MediaQueries] = providers.Dependency()

    admin_queries = providers.Factory(
        AdminQueries,
        auth_queries=providers.Dependency(), # Will be provided by main.py
        media_queries=media_queries
    )