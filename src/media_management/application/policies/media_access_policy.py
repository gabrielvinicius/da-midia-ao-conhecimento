"""Acesso às mídias: a regra comum (dono ou administrador, 404) aplicada à mídia."""

from typing import Optional
from uuid import UUID

from src.media_management.domain import Media
from src.shared.application.access import Requester, ensure_can_access
from src.shared.domain.roles import UserRole


class MediaAccessPolicy:
    def can_access(self, media: Media, user_id: UUID, user_role: Optional[UserRole] = None) -> bool:
        return Requester(user_id, user_role or UserRole.USER).owns(media.user_id)

    def ensure_can_access(self, media: Media, user_id: UUID, user_role: Optional[UserRole] = None) -> None:
        """Mídia de outro usuário é tratada como inexistente (404)."""
        ensure_can_access(media.user_id, Requester(user_id, user_role or UserRole.USER), "Mídia não encontrada")
