# src/auth/domain/interfaces.py
from abc import ABC, abstractmethod
from uuid import UUID

from src.auth.domain.user import User


class IUserPermissionService(ABC):
    @abstractmethod
    def validate_admin_operation(self, admin_user: User, target_user_id: UUID) -> None:
        pass
