# src.user_management/domain/interfaces.py
from abc import ABC, abstractmethod
from uuid import UUID

from src.user_management.domain.user import User


class IUserPermissionService(ABC):
    @abstractmethod
    def validate_admin_operation(self, admin_user: User, target_user_id: UUID) -> None:
        pass
