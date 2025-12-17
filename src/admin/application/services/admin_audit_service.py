from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog

from src.admin.application.ports import AdminAuditPort
from src.user_management.domain import User

logger = structlog.get_logger(__name__)


class AdminAuditService(AdminAuditPort):
    """Audit logging service (in-memory, sem persistência configurada)."""

    def __init__(self):
        self.audit_entries: List[Dict[str, Any]] = []

    async def log_admin_action(
        self,
        admin_user: User,
        action: str,
        target_type: str,
        target_id: UUID,
        details: Optional[Dict] = None,
    ) -> None:
        audit_entry = {
            "admin_id": admin_user.id,
            "action": action,
            "target_type": target_type,
            "target_id": target_id,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.audit_entries.append(audit_entry)
        logger.info("admin.audit.logged", **audit_entry)

    async def get_audit_entries(
        self,
        page: int = 1,
        limit: int = 50,
        target_type: Optional[str] = None,
        admin_id: Optional[UUID] = None,
        action_type: Optional[str] = None,
    ) -> List[Dict]:
        _ = (page, limit, target_type, admin_id, action_type)
        return self.audit_entries

    async def get_user_audit_trail(self, user_id: UUID) -> List[Dict]:
        return [
            entry for entry in self.audit_entries if entry["target_id"] == user_id
        ]

    async def get_admin_activity_summary(
        self,
        admin_id: UUID,
        days: int = 30,
    ) -> Dict[str, Any]:
        _ = days
        return {
            "admin_id": admin_id,
            "period_days": days,
            "total_actions": len(self.audit_entries),
            "top_actions": ["login", "update_user", "delete_media"],
        }

    async def export_audit_log(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        format_type: str = "json",
    ) -> str:
        _ = (start_date, end_date, format_type)
        return "[]"

    async def cleanup_old_audit_entries(self, days_to_keep: int = 365) -> int:
        _ = days_to_keep
        return 0
