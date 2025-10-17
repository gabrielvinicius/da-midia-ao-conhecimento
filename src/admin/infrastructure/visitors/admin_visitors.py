"""
Admin Visitors using Visitor Pattern for administrative operations
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.shared.patterns.visitor import (
    BaseVisitor, IVisitable, LeafElement, CompositeElement, 
    VisitorResult, VisitorRegistry
)


class UserRole(str, Enum):
    """User roles"""
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    GUEST = "guest"


class PermissionLevel(str, Enum):
    """Permission levels"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"


@dataclass
class UserData:
    """User data structure"""
    user_id: str
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    permissions: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MediaData:
    """Media data structure"""
    media_id: str
    user_id: str
    filename: str
    file_size: int
    mime_type: str
    upload_date: datetime
    processing_status: str
    is_public: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class SystemResource:
    """System resource data"""
    resource_id: str
    resource_type: str
    name: str
    owner_id: str
    permissions: Dict[str, List[str]]
    created_at: datetime
    last_modified: datetime
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class UserElement(LeafElement):
    """Visitable element for user data"""
    
    def __init__(self, user: UserData):
        super().__init__(f"User_{user.username}", user)
        self.user = user
    
    def get_element_type(self) -> str:
        return "User"


class MediaElement(LeafElement):
    """Visitable element for media data"""
    
    def __init__(self, media: MediaData):
        super().__init__(f"Media_{media.filename}", media)
        self.media = media
    
    def get_element_type(self) -> str:
        return "Media"


class ResourceElement(LeafElement):
    """Visitable element for system resources"""
    
    def __init__(self, resource: SystemResource):
        super().__init__(f"Resource_{resource.name}", resource)
        self.resource = resource
    
    def get_element_type(self) -> str:
        return "Resource"


class AdminDataContainer(CompositeElement):
    """Container for administrative data"""
    
    def __init__(self, name: str):
        super().__init__(name)
        self.users: List[UserElement] = []
        self.media: List[MediaElement] = []
        self.resources: List[ResourceElement] = []
    
    def add_user(self, user: UserData) -> None:
        """Add user to container"""
        element = UserElement(user)
        self.add_child(element)
        self.users.append(element)
    
    def add_media(self, media: MediaData) -> None:
        """Add media to container"""
        element = MediaElement(media)
        self.add_child(element)
        self.media.append(element)
    
    def add_resource(self, resource: SystemResource) -> None:
        """Add resource to container"""
        element = ResourceElement(resource)
        self.add_child(element)
        self.resources.append(element)
    
    def get_element_type(self) -> str:
        return "AdminDataContainer"


class SecurityAuditVisitor(BaseVisitor[Dict[str, Any]]):
    """Visitor for security auditing"""
    
    def __init__(self):
        super().__init__("SecurityAuditVisitor")
        self.security_issues = []
        self.user_analysis = {}
        self.permission_analysis = {}
    
    def visit_User(self, element: UserElement) -> Dict[str, Any]:
        """Audit user security"""
        user = element.user
        issues = []
        
        # Check for inactive users with admin privileges
        if user.role == UserRole.ADMIN and not user.is_active:
            issues.append("Inactive admin account")
        
        # Check for users without recent login
        if user.last_login:
            days_since_login = (datetime.now() - user.last_login).days
            if days_since_login > 90:
                issues.append(f"No login for {days_since_login} days")
        else:
            issues.append("Never logged in")
        
        # Check for weak permission patterns
        if user.role == UserRole.USER and "admin" in user.permissions:
            issues.append("Regular user with admin permissions")
        
        # Record findings
        audit_result = {
            "user_id": user.user_id,
            "username": user.username,
            "role": user.role.value,
            "is_active": user.is_active,
            "security_issues": issues,
            "risk_level": self._calculate_risk_level(user, issues)
        }
        
        if issues:
            self.security_issues.extend([
                {
                    "type": "user_security",
                    "user_id": user.user_id,
                    "issue": issue,
                    "severity": "medium" if "admin" in issue.lower() else "low"
                }
                for issue in issues
            ])
        
        self.user_analysis[user.user_id] = audit_result
        
        return audit_result
    
    def visit_Media(self, element: MediaElement) -> Dict[str, Any]:
        """Audit media security"""
        media = element.media
        issues = []
        
        # Check for large files that might impact performance
        if media.file_size > 100 * 1024 * 1024:  # 100MB
            issues.append("Large file size")
        
        # Check for public media without proper controls
        if media.is_public and media.processing_status != "completed":
            issues.append("Public media not fully processed")
        
        # Check for suspicious file types
        suspicious_types = ["application/x-executable", "application/x-msdownload"]
        if media.mime_type in suspicious_types:
            issues.append("Potentially dangerous file type")
        
        audit_result = {
            "media_id": media.media_id,
            "filename": media.filename,
            "file_size": media.file_size,
            "security_issues": issues,
            "risk_level": "high" if any("dangerous" in issue for issue in issues) else "low"
        }
        
        if issues:
            self.security_issues.extend([
                {
                    "type": "media_security",
                    "media_id": media.media_id,
                    "issue": issue,
                    "severity": "high" if "dangerous" in issue else "medium"
                }
                for issue in issues
            ])
        
        return audit_result
    
    def visit_Resource(self, element: ResourceElement) -> Dict[str, Any]:
        """Audit resource permissions"""
        resource = element.resource
        issues = []
        
        # Check for overly permissive resources
        total_permissions = sum(len(perms) for perms in resource.permissions.values())
        if total_permissions > 10:
            issues.append("Too many permissions granted")
        
        # Check for resources without owners
        if not resource.owner_id:
            issues.append("Resource without owner")
        
        # Check for admin permissions on regular resources
        admin_users = [user for user, perms in resource.permissions.items() 
                      if "admin" in perms]
        if len(admin_users) > 3:
            issues.append("Too many admin users")
        
        audit_result = {
            "resource_id": resource.resource_id,
            "resource_type": resource.resource_type,
            "name": resource.name,
            "security_issues": issues,
            "admin_count": len(admin_users),
            "total_permissions": total_permissions
        }
        
        if issues:
            self.security_issues.extend([
                {
                    "type": "resource_security",
                    "resource_id": resource.resource_id,
                    "issue": issue,
                    "severity": "medium"
                }
                for issue in issues
            ])
        
        return audit_result
    
    def _create_default_result(self, element: IVisitable) -> Dict[str, Any]:
        return {"type": "security_unknown"}
    
    def _calculate_risk_level(self, user: UserData, issues: List[str]) -> str:
        """Calculate user risk level"""
        if user.role == UserRole.ADMIN and issues:
            return "high"
        elif len(issues) > 2:
            return "medium"
        elif issues:
            return "low"
        else:
            return "none"
    
    def get_security_report(self) -> Dict[str, Any]:
        """Generate comprehensive security report"""
        
        # Categorize issues by severity
        issues_by_severity = {"high": [], "medium": [], "low": []}
        for issue in self.security_issues:
            issues_by_severity[issue["severity"]].append(issue)
        
        # Calculate summary statistics
        total_users = len(self.user_analysis)
        high_risk_users = sum(1 for analysis in self.user_analysis.values() 
                             if analysis["risk_level"] == "high")
        
        return {
            "total_issues": len(self.security_issues),
            "issues_by_severity": {k: len(v) for k, v in issues_by_severity.items()},
            "detailed_issues": issues_by_severity,
            "user_summary": {
                "total_users": total_users,
                "high_risk_users": high_risk_users,
                "risk_percentage": (high_risk_users / total_users * 100) if total_users > 0 else 0
            },
            "recommendations": self._generate_security_recommendations()
        }
    
    def _generate_security_recommendations(self) -> List[str]:
        """Generate security recommendations"""
        recommendations = []
        
        if len(self.security_issues) > 0:
            recommendations.append("Review and address identified security issues")
        
        high_severity_count = sum(1 for issue in self.security_issues 
                                 if issue["severity"] == "high")
        if high_severity_count > 0:
            recommendations.append("Prioritize high-severity security issues")
        
        recommendations.extend([
            "Implement regular security audits",
            "Review user permissions quarterly",
            "Monitor inactive admin accounts"
        ])
        
        return recommendations


class ComplianceCheckVisitor(BaseVisitor[Dict[str, Any]]):
    """Visitor for compliance checking"""
    
    def __init__(self, compliance_rules: Dict[str, Any] = None):
        super().__init__("ComplianceCheckVisitor")
        self.compliance_rules = compliance_rules or self._default_compliance_rules()
        self.violations = []
        self.compliance_scores = {}
    
    def visit_User(self, element: UserElement) -> Dict[str, Any]:
        """Check user compliance"""
        user = element.user
        violations = []
        
        # Data retention compliance
        account_age_days = (datetime.now() - user.created_at).days
        max_inactive_days = self.compliance_rules.get("max_inactive_days", 365)
        
        if not user.is_active and account_age_days > max_inactive_days:
            violations.append("Account retention violation")
        
        # Email domain compliance
        allowed_domains = self.compliance_rules.get("allowed_email_domains", [])
        if allowed_domains:
            email_domain = user.email.split("@")[1] if "@" in user.email else ""
            if email_domain not in allowed_domains:
                violations.append("Email domain not compliant")
        
        # Role assignment compliance
        if user.role == UserRole.ADMIN:
            required_permissions = self.compliance_rules.get("admin_required_permissions", [])
            missing_permissions = [p for p in required_permissions if p not in user.permissions]
            if missing_permissions:
                violations.append(f"Missing required permissions: {missing_permissions}")
        
        compliance_result = {
            "user_id": user.user_id,
            "violations": violations,
            "compliant": len(violations) == 0,
            "compliance_score": self._calculate_compliance_score(violations)
        }
        
        if violations:
            self.violations.extend([
                {
                    "type": "user_compliance",
                    "user_id": user.user_id,
                    "violation": violation,
                    "severity": "high" if "admin" in violation.lower() else "medium"
                }
                for violation in violations
            ])
        
        self.compliance_scores[user.user_id] = compliance_result["compliance_score"]
        
        return compliance_result
    
    def visit_Media(self, element: MediaElement) -> Dict[str, Any]:
        """Check media compliance"""
        media = element.media
        violations = []
        
        # File size compliance
        max_file_size = self.compliance_rules.get("max_file_size_mb", 50) * 1024 * 1024
        if media.file_size > max_file_size:
            violations.append("File size exceeds limit")
        
        # File type compliance
        allowed_mime_types = self.compliance_rules.get("allowed_mime_types", [])
        if allowed_mime_types and media.mime_type not in allowed_mime_types:
            violations.append("File type not allowed")
        
        # Processing compliance
        max_processing_days = self.compliance_rules.get("max_processing_days", 7)
        processing_age = (datetime.now() - media.upload_date).days
        if media.processing_status == "processing" and processing_age > max_processing_days:
            violations.append("Processing time exceeds limit")
        
        compliance_result = {
            "media_id": media.media_id,
            "violations": violations,
            "compliant": len(violations) == 0
        }
        
        if violations:
            self.violations.extend([
                {
                    "type": "media_compliance",
                    "media_id": media.media_id,
                    "violation": violation,
                    "severity": "medium"
                }
                for violation in violations
            ])
        
        return compliance_result
    
    def _create_default_result(self, element: IVisitable) -> Dict[str, Any]:
        return {"type": "compliance_unknown"}
    
    def _default_compliance_rules(self) -> Dict[str, Any]:
        """Default compliance rules"""
        return {
            "max_inactive_days": 365,
            "max_file_size_mb": 50,
            "max_processing_days": 7,
            "allowed_email_domains": [],
            "allowed_mime_types": [
                "image/jpeg", "image/png", "video/mp4", 
                "audio/mp3", "text/plain", "application/pdf"
            ],
            "admin_required_permissions": ["user_management", "system_admin"]
        }
    
    def _calculate_compliance_score(self, violations: List[str]) -> float:
        """Calculate compliance score (0.0 to 1.0)"""
        if not violations:
            return 1.0
        
        # Decrease score based on number and severity of violations
        base_score = 1.0
        for violation in violations:
            if "admin" in violation.lower() or "required" in violation.lower():
                base_score -= 0.3  # Major violations
            else:
                base_score -= 0.1  # Minor violations
        
        return max(0.0, base_score)
    
    def get_compliance_report(self) -> Dict[str, Any]:
        """Generate compliance report"""
        
        total_violations = len(self.violations)
        violations_by_type = {}
        for violation in self.violations:
            v_type = violation["type"]
            if v_type not in violations_by_type:
                violations_by_type[v_type] = 0
            violations_by_type[v_type] += 1
        
        # Calculate overall compliance score
        overall_score = (
            sum(self.compliance_scores.values()) / len(self.compliance_scores)
            if self.compliance_scores else 1.0
        )
        
        return {
            "overall_compliance_score": overall_score,
            "total_violations": total_violations,
            "violations_by_type": violations_by_type,
            "detailed_violations": self.violations,
            "compliance_status": "compliant" if overall_score >= 0.8 else "non_compliant",
            "recommendations": self._generate_compliance_recommendations()
        }
    
    def _generate_compliance_recommendations(self) -> List[str]:
        """Generate compliance recommendations"""
        recommendations = []
        
        if len(self.violations) > 0:
            recommendations.append("Address identified compliance violations")
        
        recommendations.extend([
            "Implement automated compliance monitoring",
            "Regular compliance training for staff",
            "Review and update compliance rules quarterly"
        ])
        
        return recommendations


class SystemCleanupVisitor(BaseVisitor[Dict[str, Any]]):
    """Visitor for identifying cleanup opportunities"""
    
    def __init__(self):
        super().__init__("SystemCleanupVisitor")
        self.cleanup_candidates = []
        self.cleanup_stats = {}
    
    def visit_User(self, element: UserElement) -> Dict[str, Any]:
        """Identify users for cleanup"""
        user = element.user
        
        # Inactive users
        if not user.is_active:
            inactive_days = (datetime.now() - (user.last_login or user.created_at)).days
            if inactive_days > 180:  # 6 months
                self.cleanup_candidates.append({
                    "type": "inactive_user",
                    "user_id": user.user_id,
                    "username": user.username,
                    "inactive_days": inactive_days,
                    "action": "consider_deletion",
                    "priority": "high" if inactive_days > 365 else "medium"
                })
        
        # Users with no permissions
        if not user.permissions and user.role == UserRole.USER:
            self.cleanup_candidates.append({
                "type": "no_permissions_user",
                "user_id": user.user_id,
                "action": "review_permissions",
                "priority": "low"
            })
        
        return {
            "user_id": user.user_id,
            "cleanup_needed": len([c for c in self.cleanup_candidates 
                                 if c.get("user_id") == user.user_id]) > 0
        }
    
    def visit_Media(self, element: MediaElement) -> Dict[str, Any]:
        """Identify media for cleanup"""
        media = element.media
        
        # Old processed media
        age_days = (datetime.now() - media.upload_date).days
        if age_days > 365 and media.processing_status == "completed":
            self.cleanup_candidates.append({
                "type": "old_media",
                "media_id": media.media_id,
                "age_days": age_days,
                "file_size": media.file_size,
                "action": "archive_or_delete",
                "priority": "low"
            })
        
        # Failed processing media
        if media.processing_status == "failed" and age_days > 30:
            self.cleanup_candidates.append({
                "type": "failed_media",
                "media_id": media.media_id,
                "action": "delete",
                "priority": "medium"
            })
        
        return {
            "media_id": media.media_id,
            "cleanup_needed": len([c for c in self.cleanup_candidates 
                                 if c.get("media_id") == media.media_id]) > 0
        }
    
    def _create_default_result(self, element: IVisitable) -> Dict[str, Any]:
        return {"type": "cleanup_unknown"}
    
    def get_cleanup_report(self) -> Dict[str, Any]:
        """Generate cleanup report"""
        
        # Group by type and priority
        by_type = {}
        by_priority = {"high": [], "medium": [], "low": []}
        
        for candidate in self.cleanup_candidates:
            c_type = candidate["type"]
            priority = candidate["priority"]
            
            if c_type not in by_type:
                by_type[c_type] = []
            by_type[c_type].append(candidate)
            by_priority[priority].append(candidate)
        
        # Calculate potential storage savings
        storage_savings = sum(
            candidate.get("file_size", 0) 
            for candidate in self.cleanup_candidates 
            if candidate["type"] in ["old_media", "failed_media"]
        )
        
        return {
            "total_cleanup_candidates": len(self.cleanup_candidates),
            "candidates_by_type": {k: len(v) for k, v in by_type.items()},
            "candidates_by_priority": {k: len(v) for k, v in by_priority.items()},
            "detailed_candidates": by_type,
            "potential_storage_savings_bytes": storage_savings,
            "recommendations": [
                "Review high-priority cleanup candidates first",
                "Archive old media before deletion",
                "Implement automated cleanup policies"
            ]
        }


# Register admin visitors
def register_admin_visitors():
    """Register all admin visitors"""
    
    VisitorRegistry.register_visitor(
        "security_audit_visitor",
        SecurityAuditVisitor,
        "admin"
    )
    
    VisitorRegistry.register_visitor(
        "compliance_check_visitor",
        ComplianceCheckVisitor,
        "admin"
    )
    
    VisitorRegistry.register_visitor(
        "system_cleanup_visitor", 
        SystemCleanupVisitor,
        "admin"
    )