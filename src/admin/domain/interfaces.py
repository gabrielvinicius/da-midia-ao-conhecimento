# src/admin/domain/interfaces.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID

from src.user_management.domain.user import User
from src.media_management.domain.media import Media, MediaStatus


class IAdminUserService(ABC):
    @abstractmethod
    async def update_user_role(self, user_id: UUID, new_role: str, admin_user: User) -> User:
        pass

    @abstractmethod
    async def delete_user(self, user_id: UUID, admin_user: User) -> None:
        pass

    @abstractmethod
    async def activate_user(self, user_id: UUID, admin_user: User) -> User:
        pass

    @abstractmethod
    async def deactivate_user(self, user_id: UUID, admin_user: User) -> User:
        pass

    @abstractmethod
    async def bulk_update_users(self, user_updates: List[Dict], admin_user: User) -> List[User]:
        pass


class IAdminMediaService(ABC):
    @abstractmethod
    async def delete_media(self, media_id: UUID, admin_user: User) -> None:
        pass

    @abstractmethod
    async def reprocess_media(self, media_id: UUID, admin_user: User) -> None:
        pass

    @abstractmethod
    async def bulk_reprocess_failed_media(self, admin_user: User) -> int:
        pass

    @abstractmethod
    async def cleanup_orphaned_files(self, admin_user: User) -> int:
        pass

    @abstractmethod
    async def get_media_by_status(self, status: MediaStatus) -> List[Media]:
        pass

    @abstractmethod
    async def get_media_processing_queue_info(self) -> dict:
        pass

    @abstractmethod
    async def force_media_status_change(
        self,
        media_id: UUID,
        new_status: MediaStatus,
        admin_user: User,
        reason: str,
    ) -> None:
        pass


class IAdminAuditService(ABC):
    @abstractmethod
    async def log_admin_action(
        self,
        admin_user: User,
        action: str,
        target_type: str,
        target_id: UUID,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        pass
