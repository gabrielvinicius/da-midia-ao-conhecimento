from __future__ import annotations

from typing import Any, Dict, Optional
from uuid import UUID

from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.user_management.domain import User, UserRole

from .user_service import UserService

logger = get_logger(__name__)


class AuthService:
    """Thin facade over UserService kept for compatibility with API wiring."""

    def __init__(
        self,
        user_service: UserService,
        settings: Any,
    ) -> None:
        self.user_service = user_service
        self.settings = settings

    async def authenticate_user(self, email: str, password: str) -> dict[str, Any]:
        logger.info("auth.authenticate.started", email=email)
        try:
            result = await self.user_service.authenticate_user(email, password)
        except ValueError:
            logger.warning(
                "auth.authenticate.failed",
                email=email,
                reason="invalid_credentials",
            )
            raise
        logger.info("auth.authenticate.success", email=email)
        return result

    # Sync methods removed or deprecated as UserService is async-only
    # def authenticate_user_sync(self, email: str, password: str) -> dict[str, Any]: ...

    async def create_user(self, email: str, password: str, role: str = "user"):
        from ..dtos import CreateUserCommand
        return await self.user_service.create_user(
            CreateUserCommand(
                email=email,
                password=password,
                role=UserRole(role.upper()),
            )
        )

    async def update_user(
        self,
        user_id: UUID,
        updates: Dict[str, Any],
        admin_user_id: Optional[UUID] = None,
    ):
        logger.info(
            "user.update.started",
            user_id=str(user_id),
            updates=updates,
            admin_user_id=str(admin_user_id),
        )
        from ..dtos import UpdateUserCommand
        # Mapping updates dict to Command
        cmd = UpdateUserCommand(
            user_id=user_id,
            email=updates.get("email"),
            password=updates.get("password"),
            role=UserRole(updates.get("role").upper()) if updates.get("role") else None,
            is_active=updates.get("is_active"),
        )
        updated = await self.user_service.update_user(cmd)
        logger.info("user.update.completed", user_id=str(updated.id))
        return updated

    async def delete_user(
        self, user_id: UUID, admin_user_id: Optional[UUID] = None
    ) -> bool:
        logger.info(
            "user.delete.started",
            user_id=str(user_id),
            admin_user_id=str(admin_user_id),
        )
        from ..dtos import DeleteUserCommand
        await self.user_service.delete_user(DeleteUserCommand(user_id=user_id))
        logger.info("user.delete.completed", user_id=str(user_id))
        return True

    async def change_password(
        self, user_id: UUID, old_password: str, new_password: str
    ) -> bool:
        await self.user_service.change_password(user_id, old_password, new_password)
        return True

    def require_admin_role(self, user: User) -> None:
        if user.role != UserRole.ADMIN:
            raise PermissionError("Perfil de admin é obrigatório")

    def can_modify_user(self, current_user: User, target_user_id: UUID) -> bool:
        if current_user.role == UserRole.ADMIN:
            return True
        return str(current_user.id) == str(target_user_id)

    async def get_user_by_id(self, user_id: UUID):
        return await self.user_service.user_read_service.get_user_by_id(user_id)

    async def get_user_by_email(self, email: str):
        return await self.user_service.user_read_service.get_user_by_email(email)

    async def list_users(self) -> list[User]:
        from ..dtos import ListUsersQuery
        return await self.user_service.user_read_service.list_all()
