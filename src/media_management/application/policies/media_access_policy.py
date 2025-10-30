"""Access control policy for media operations."""

from typing import Optional
from uuid import UUID

from src.user_management.domain.user import UserRole
from src.media_management.domain.media import Media


class MediaAccessPolicy:
    """Defines reusable access checks for media resources."""

    @staticmethod
    def _normalize_role(user_role: Optional[UserRole]) -> str:
        if isinstance(user_role, UserRole):
            return user_role.value
        return str(user_role or UserRole.USER.value)

    def can_access(self, media: Media, user_id: UUID, user_role: Optional[UserRole] = None) -> bool:
        """Return True if the user can access the provided media."""

        role_value = self._normalize_role(user_role)
        if role_value == UserRole.ADMIN.value:
            return True
        return str(media.user_id) == str(user_id)

    def ensure_can_access(self, media: Media, user_id: UUID, user_role: Optional[UserRole] = None) -> None:
        """Raise PermissionError when the user lacks access to the media."""

        if not self.can_access(media, user_id, user_role):
            raise PermissionError("User is not authorized to access this media")

    # Additional helpers can be added here when needed.
