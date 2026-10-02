"""Adaptadores do admin sobre os módulos de mídias e de usuários."""
from __future__ import annotations

from src.admin.infrastructure.adapters.media_management_adapter import (
    MediaManagementAdapter,
)
from src.admin.infrastructure.adapters.media_read_adapter import MediaReadAdapter
from src.admin.infrastructure.adapters.user_management_adapter import (
    UserManagementAdapter,
)
from src.admin.infrastructure.adapters.user_read_adapter import UserReadAdapter
from src.media_management.application.services.media_read_service import (
    MediaReadService,
)
from src.media_management.application.services.media_service import MediaService
from src.media_management.infrastructure.repositories.media_repository import (
    MediaRepository,
)
from src.user_management.application.auth_queries import UserReadService
from src.user_management.application.services.user_service import UserService


def get_media_admin_adapter(media_service: MediaService, session) -> MediaManagementAdapter:
    return MediaManagementAdapter(media_service, MediaRepository(db=session))


def get_user_admin_adapter(
    user_service: UserService,
    auth_queries: UserReadService,
) -> UserManagementAdapter:
    return UserManagementAdapter(
        user_service=user_service,
        user_read_service=auth_queries,
    )


def get_media_read_adapter(media_read_service: MediaReadService) -> MediaReadAdapter:
    """Leitura das mídias pelo serviço do próprio módulo de mídias (sua montagem única)."""
    return MediaReadAdapter(media_read_service)


def get_user_read_adapter(auth_queries: UserReadService) -> UserReadAdapter:
    return UserReadAdapter(auth_queries)


__all__ = [
    "get_media_admin_adapter",
    "get_user_admin_adapter",
    "get_media_read_adapter",
    "get_user_read_adapter",
]
