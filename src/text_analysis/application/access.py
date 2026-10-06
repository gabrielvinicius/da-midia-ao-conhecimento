"""Quem pode ver e alterar uma análise: o dono da mídia ou um administrador.

Antes, cada rota fazia a sua checagem; a da análise respondia 403, o que
confirmava que o id existia. Aqui a resposta é sempre 404, como nas mídias.
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
    role: UserRole

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN


def ensure_can_access(owner_id: Optional[object], requester: Requester, what: str = "Análise") -> None:
    """Sem dono registrado, só o administrador vê (antes, qualquer um via)."""
    if requester.is_admin:
        return
    if owner_id is None or str(owner_id) != str(requester.user_id):
        raise NotFoundError(f"{what} não encontrada")


__all__ = ["Requester", "ensure_can_access"]
