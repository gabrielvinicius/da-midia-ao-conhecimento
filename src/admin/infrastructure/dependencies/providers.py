"""Registry for admin facade adapters."""
from __future__ import annotations

from src.admin.application.services.admin_user_service import AdminUserService
from src.admin.infrastructure.adapters.media_management_adapter import (
    MediaManagementAdapter,
)
from src.admin.infrastructure.adapters.media_read_adapter import MediaReadAdapter
from src.admin.infrastructure.adapters.media_repository_adapter import (
    MediaRepositoryAdapter,
)
from src.admin.infrastructure.adapters.user_management_adapter import (
    UserManagementAdapter,
)
from src.admin.infrastructure.adapters.user_read_adapter import UserReadAdapter
from src.admin.infrastructure.adapters.user_repository_adapter import (
    UserRepositoryAdapter,
)
from src.media_management.application.services.media_read_service import (
    MediaReadService,
)
from src.media_management.application.services.media_service import MediaService
from src.media_management.infrastructure.repositories.media_repository import (
    MediaRepository,
)
from src.user_management.application.auth_queries import UserReadService
from src.user_management.infrastructure.repositories.sqlalchemy_user_repository import (
    UserRepository,
)


def get_media_admin_adapter(
    media_service: MediaService,
    admin_media_service,
    auth_queries: UserReadService,
) -> MediaManagementAdapter:
    return MediaManagementAdapter(
        media_service=media_service,
        admin_media_service=admin_media_service,
        auth_queries=auth_queries,
    )


def get_user_admin_adapter(
    auth_queries: UserReadService,
    admin_user_service: AdminUserService,
) -> UserManagementAdapter:
    return UserManagementAdapter(
        auth_queries=auth_queries,
        admin_user_service=admin_user_service,
    )


def get_media_repository_adapter(session) -> MediaRepositoryAdapter:
    return MediaRepositoryAdapter(MediaRepository(db=session))


def get_user_repository_adapter(session) -> UserRepositoryAdapter:
    return UserRepositoryAdapter(UserRepository(db=session))


def get_media_read_adapter(media_repository) -> MediaReadAdapter:
    return MediaReadAdapter(MediaReadService(media_repository))


def get_user_read_adapter(auth_queries: UserReadService) -> UserReadAdapter:
    return UserReadAdapter(auth_queries)


__all__ = [
    "get_media_admin_adapter",
    "get_user_admin_adapter",
    "get_media_repository_adapter",
    "get_user_repository_adapter",
    "get_media_read_adapter",
    "get_user_read_adapter",
]
