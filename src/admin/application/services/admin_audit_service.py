"""Registro das ações dos administradores.

Cada ação vira uma linha do log estruturado (JSON), com o identificador de
correlação da requisição, e é coletada com os demais logs. Antes, as ações
iam também para uma lista em memória, que crescia sem limite enquanto a API
rodava e se perdia ao reiniciar, e havia consultas sobre essa lista que
devolviam dados fixos (ações "mais comuns" inventadas, exportação vazia),
sem uso em lugar nenhum.
"""
from typing import Dict, Optional
from uuid import UUID

import structlog

from src.admin.application.ports import AdminAuditPort
from src.user_management.domain import User

logger = structlog.get_logger("admin.audit")


class AdminAuditService(AdminAuditPort):
    async def log_admin_action(
        self,
        admin_user: User,
        action: str,
        target_type: str,
        target_id: UUID,
        details: Optional[Dict] = None,
    ) -> None:
        logger.info(
            "admin.audit",
            admin_id=str(admin_user.id),
            action=action,
            target_type=target_type,
            target_id=str(target_id),
            details=details or {},
        )


__all__ = ["AdminAuditService"]
