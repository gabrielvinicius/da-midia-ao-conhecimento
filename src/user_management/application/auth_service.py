from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog

from src.user_management.application.user_service import UserService
from src.user_management.domain.user import User, UserRole

logger = structlog.get_logger(__name__)


class AuthService:
    """Thin facade over UserService kept for compatibility with API wiring.
    """

    def __init__(
        self,
        user_service: UserService,
        settings: Any,
    ) -> None:
        self.user_service = user_service
        self.settings = settings

    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        logger.info("auth.authenticate.started", email=email)
        try:
            result = await self.user_service.authenticate_user(email, password)
        except ValueError:
            logger.warning("auth.authenticate.failed", email=email, reason="invalid_credentials")
            raise
        logger.info("auth.authenticate.success", email=email)
        return result

    def authenticate_user_sync(self, email: str, password: str) -> Dict[str, Any]:
        logger.info("auth.authenticate.started_sync", email=email)
        try:
            result = self.user_service.authenticate_user_sync(email, password)
        except ValueError:
            logger.warning("auth.authenticate.failed_sync", email=email, reason="invalid_credentials")
            raise
        logger.info("auth.authenticate.success_sync", email=email)
        return result

    async def create_user(self, email: str, password: str, role: str = "user"):
        return await self.user_service.create_user(email=email, password=password, role=role)

    def create_user_sync(self, email: str, password: str, role: str = "user"):
        return self.user_service.create_user_sync(email=email, password=password, role=role)

    async def update_user(self, user_id: UUID, updates: Dict[str, Any], admin_user_id: Optional[UUID] = None):
        logger.info("user.update.started", user_id=str(user_id), updates=updates, admin_user_id=str(admin_user_id))
        updated = await self.user_service.update_user(user_id, updates)
        logger.info("user.update.completed", user_id=str(updated.id))
        return updated

    def update_user_sync(self, user_id: UUID, updates: Dict[str, Any], admin_user_id: Optional[UUID] = None):
        logger.info("user.update.started_sync", user_id=str(user_id), updates=updates, admin_user_id=str(admin_user_id))
        updated = self.user_service.update_user_sync(user_id, updates)
        logger.info("user.update.completed_sync", user_id=str(updated.id))
        return updated

    async def delete_user(self, user_id: UUID, admin_user_id: Optional[UUID] = None) -> bool:
        logger.info("user.delete.started", user_id=str(user_id), admin_user_id=str(admin_user_id))
        await self.user_service.delete_user(user_id)
        logger.info("user.delete.completed", user_id=str(user_id))
        return True

    def delete_user_sync(self, user_id: UUID, admin_user_id: Optional[UUID] = None) -> bool:
        logger.info("user.delete.started_sync", user_id=str(user_id), admin_user_id=str(admin_user_id))
        self.user_service.delete_user_sync(user_id)
        logger.info("user.delete.completed_sync", user_id=str(user_id))
        return True

    async def change_password(self, user_id: UUID, old_password: str, new_password: str) -> bool:
        await self.user_service.change_password(user_id, old_password, new_password)
        return True

    def change_password_sync(self, user_id: UUID, old_password: str, new_password: str) -> bool:
        self.user_service.change_password_sync(user_id, old_password, new_password)
        return True

    def require_admin_role(self, user: User) -> None:
        if user.role != UserRole.ADMIN:
            raise PermissionError("Admin role required")

    def can_modify_user(self, current_user: User, target_user_id: UUID) -> bool:
        if current_user.role == UserRole.ADMIN:
            return True
        return str(current_user.id) == str(target_user_id)

    async def get_user_by_id(self, user_id: UUID):
        return await self.user_service.get_user_by_id(user_id)

    def get_user_by_id_sync(self, user_id: UUID):
        return self.user_service.get_user_by_id_sync(user_id)

    async def get_user_by_email(self, email: str):
        return await self.user_service.get_user_by_email(email)

    def get_user_by_email_sync(self, email: str):
        return self.user_service.get_user_by_email_sync(email)

    async def list_users(self) -> List[User]:
        return await self.user_service.list_users()

    def list_users_sync(self) -> List[User]:
        return self.user_service.list_users_sync()
