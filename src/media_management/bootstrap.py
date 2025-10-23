# src/media_management/bootstrap.py
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.infrastructure.logging import StructuredMediaLogger
from src.media_management.infrastructure.metrics import PrometheusMediaMetrics
from src.media_management.application.commands.handlers import DeleteMediaCommandHandler, ReprocessMediaCommandHandler
from src.media_management.application.media_service import MediaService
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.config.settings import MediaSettings

class MediaManagementContainer(containers.DeclarativeContainer):
    # Dependências de infraestrutura
    db: providers.Provider[AsyncSession] = providers.Dependency()

    # Config
    media_settings = providers.Singleton(MediaSettings)

    # Implementações concretas
    media_repository = providers.Factory(
        MediaRepository,
        db=db
    )
    media_queries = providers.Factory(
        MediaQueries,
        media_repository=media_repository
    )
    media_logger = providers.Singleton(
        StructuredMediaLogger
    )
    media_metrics = providers.Singleton(
        PrometheusMediaMetrics
    )

    # Command Handlers (Delete and Reprocess remain for now)
    delete_media_command_handler = providers.Factory(
        DeleteMediaCommandHandler,
        media_repo=media_repository,
        media_logger=media_logger,
        media_metrics=media_metrics
    )
    reprocess_media_command_handler = providers.Factory(
        ReprocessMediaCommandHandler,
        media_repo=media_repository,
        media_logger=media_logger,
        media_metrics=media_metrics
    )

    # Serviços de Aplicação
    media_service = providers.Factory(
        MediaService,
        media_repo=media_repository,
        media_queries=media_queries,
        delete_media_handler=delete_media_command_handler,
        reprocess_media_handler=reprocess_media_command_handler,
        media_logger=media_logger,
        media_metrics=media_metrics,
        media_settings=media_settings,
    )