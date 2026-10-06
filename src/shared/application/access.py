"""Quem pode ver um recurso de um usuário: o dono ou um administrador.

Era repetida em cada roteador (mídias, transcrições, análises), e a da
análise respondia 403, o que confirmava que o id existia. Agora há uma só
regra, aplicada pelos serviços, e a resposta é sempre 404.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from src.shared.domain.errors import NotFoundError
from src.shared.domain.roles import UserRole


@dataclass(frozen=True)
class Requester:
    user_id: UUID
    role: UserRole = UserRole.USER

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def owns(self, owner_id: Optional[object]) -> bool:
        """Sem dono registrado, só o administrador vê (antes, qualquer um via)."""
        return self.is_admin or (owner_id is not None and str(owner_id) == str(self.user_id))


def ensure_can_access(owner_id: Optional[object], requester: Requester, not_found: str) -> None:
    if not requester.owns(owner_id):
        raise NotFoundError(not_found)


__all__ = ["Requester", "ensure_can_access"]
