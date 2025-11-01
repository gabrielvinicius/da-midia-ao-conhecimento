"""
Admin Audit Service - Single Responsibility: Audit logging and tracking
Follows SRP by handling only audit-related operations.
"""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
import structlog

from src.admin.domain.interfaces import IAdminAuditService
from src.user_management.domain.user import User

logger = structlog.get_logger(__name__)


class AdminAuditService(IAdminAuditService):
    """
    Service responsible ONLY for audit logging and tracking.
    
    Single Responsibility: Handle audit trail and compliance logging.
    Open/Closed: Extensible for different audit backends.
    """
    
    def __init__(self):
        # In a real implementation, this would inject audit repository
        # For now, we'll use structured logging as the audit mechanism
        self.audit_entries = []  # Temporary in-memory storage for demo
    
    async def log_admin_action(
        self, 
        admin_user: User, 
        action: str, 
        target_type: str, 
        target_id: UUID, 
        details: Optional[Dict] = None
    ) -> None:
        """
        Log administrative action for audit trail.
        
        Args:
            admin_user: User performing the action
            action: Type of action performed
            target_type: Type of target (user, media, system)
            target_id: ID of the target
            details: Additional details about the action
        """
        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "admin_id": str(admin_user.id),
            "admin_email": admin_user.email,
            "action": action,
            "target_type": target_type,
            "target_id": str(target_id),
            "details": details or {},
            "ip_address": None,  # Would be extracted from request context
            "user_agent": None   # Would be extracted from request context
        }
        
        # Store audit entry (in real implementation, this would go to database)
        self.audit_entries.append(audit_entry)
        
        # Log to structured logger for monitoring
        logger.info(
            "admin.audit.action_logged",
            **audit_entry
        )
    
    async def get_audit_log(
        self, 
        page: int = 1, 
        limit: int = 50,
        admin_id: Optional[UUID] = None,
        action_type: Optional[str] = None
    ) -> List[Dict]:
        """
        Get audit log entries with pagination and filtering.
        
        Args:
            page: Page number for pagination
            limit: Number of entries per page
            admin_id: Filter by specific admin user
            action_type: Filter by action type
            
        Returns:
            List of audit log entries
        """
        # Filter entries
        filtered_entries = self.audit_entries.copy()
        
        if admin_id:
            filtered_entries = [
                entry for entry in filtered_entries 
                if entry["admin_id"] == str(admin_id)
            ]
        
        if action_type:
            filtered_entries = [
                entry for entry in filtered_entries 
                if entry["action"] == action_type
            ]
        
        # Sort by timestamp (newest first)
        filtered_entries.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Paginate
        start_idx = (page - 1) * limit
        end_idx = start_idx + limit
        
        return filtered_entries[start_idx:end_idx]
    
    async def get_user_audit_trail(self, user_id: UUID) -> List[Dict]:
        """
        Get audit trail for specific user (actions performed on this user).
        
        Args:
            user_id: ID of the user to get audit trail for
            
        Returns:
            List of audit entries related to this user
        """
        user_entries = [
            entry for entry in self.audit_entries
            if entry["target_id"] == str(user_id) and entry["target_type"] == "user"
        ]
        
        # Sort by timestamp (newest first)
        user_entries.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return user_entries
    
    async def get_admin_activity_summary(self, admin_id: UUID, days: int = 30) -> Dict[str, Any]:
        """
        Get activity summary for a specific admin over the last N days.
        
        Args:
            admin_id: ID of admin user
            days: Number of days to look back
            
        Returns:
            Summary of admin activity
        """
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()
        
        admin_entries = [
            entry for entry in self.audit_entries
            if (entry["admin_id"] == str(admin_id) and 
                entry["timestamp"] >= cutoff_iso)
        ]
        
        # Count actions by type
        action_counts = {}
        for entry in admin_entries:
            action = entry["action"]
            action_counts[action] = action_counts.get(action, 0) + 1
        
        # Count targets by type
        target_counts = {}
        for entry in admin_entries:
            target_type = entry["target_type"]
            target_counts[target_type] = target_counts.get(target_type, 0) + 1
        
        return {
            "admin_id": str(admin_id),
            "period_days": days,
            "total_actions": len(admin_entries),
            "actions_by_type": action_counts,
            "targets_by_type": target_counts,
            "first_action": admin_entries[-1]["timestamp"] if admin_entries else None,
            "last_action": admin_entries[0]["timestamp"] if admin_entries else None
        }
    
    async def export_audit_log(
        self, 
        start_date: datetime, 
        end_date: datetime,
        format_type: str = "json"
    ) -> str:
        """
        Export audit log for compliance purposes.
        
        Args:
            start_date: Start date for export
            end_date: End date for export
            format_type: Export format (json, csv)
            
        Returns:
            Exported data as string
        """
        start_iso = start_date.isoformat()
        end_iso = end_date.isoformat()
        
        filtered_entries = [
            entry for entry in self.audit_entries
            if start_iso <= entry["timestamp"] <= end_iso
        ]
        
        if format_type == "json":
            import json
            return json.dumps(filtered_entries, indent=2)
        elif format_type == "csv":
            # Simple CSV export implementation
            if not filtered_entries:
                return "No entries found"
            
            headers = filtered_entries[0].keys()
            csv_lines = [",".join(headers)]
            
            for entry in filtered_entries:
                row = [str(entry.get(header, "")) for header in headers]
                csv_lines.append(",".join(row))
            
            return "\n".join(csv_lines)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
    
    async def cleanup_old_audit_entries(self, days_to_keep: int = 365) -> int:
        """
        Clean up old audit entries for data retention compliance.
        
        Args:
            days_to_keep: Number of days to retain audit entries
            
        Returns:
            Number of entries removed
        """
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        cutoff_iso = cutoff_date.isoformat()
        
        original_count = len(self.audit_entries)
        
        self.audit_entries = [
            entry for entry in self.audit_entries
            if entry["timestamp"] >= cutoff_iso
        ]
        
        removed_count = original_count - len(self.audit_entries)
        
        logger.info(
            "admin.audit.cleanup_completed",
            days_to_keep=days_to_keep,
            entries_removed=removed_count,
            entries_remaining=len(self.audit_entries)
        )
        
        return removed_count
