from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.application.queries.admin_queries import AdminQueries
from src.admin.application.services.admin_audit_service import AdminAuditService
from src.admin.application.services.admin_media_service import AdminMediaService
from src.admin.application.services.admin_user_service import AdminUserService
from src.media_management.application.facade import MediaOrchestrator
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.infrastructure.media_repository import MediaRepository
from src.user_management.application.permission_service import UserPermissionService
from src.user_management.application.queries.auth_queries import AuthQueries
from src.user_management.infrastructure.user_repository import UserRepository


class AdminContainer(containers.DeclarativeContainer):
    db: providers.Provider[AsyncSession] = providers.Dependency()
    auth_queries: providers.Provider[AuthQueries] = providers.Dependency()
    media_queries: providers.Provider[MediaQueries] = providers.Dependency()
    media_orchestrator: providers.Provider[MediaOrchestrator] = providers.Dependency()

    user_repository = providers.Factory(UserRepository, db=db)
    media_repository = providers.Factory(MediaRepository, db=db)
    permission_service = providers.Factory(UserPermissionService)
    admin_audit_service = providers.Singleton(AdminAuditService)

    admin_user_service = providers.Factory(
        AdminUserService,
        user_repository=user_repository,
        permission_service=permission_service,
        audit_service=admin_audit_service,
    )

    admin_media_service = providers.Factory(
        AdminMediaService,
        media_repository=media_repository,
        permission_service=permission_service,
        audit_service=admin_audit_service,
        media_orchestrator=media_orchestrator,
    )

    admin_queries = providers.Factory(
        AdminQueries,
        auth_queries=auth_queries,
        media_queries=media_queries,
    )
