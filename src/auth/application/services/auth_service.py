"""
Consolidated Auth Service - Handles authentication, permissions, and security
Consolidates: AuthenticationService, EnhancedAuthenticationService, UserPermissionService
"""
import structlog
from typing import Dict, Any, Optional, List
from uuid import UUID
from datetime import datetime

from src.auth.domain.user import User, UserRole
from src.auth.application.commands.commands import AuthenticateUserCommand
from src.auth.application.commands.handlers import AuthenticateUserCommandHandler
from src.auth.config.settings import AuthSettings
from src.shared.monitoring.metrics_collector import MetricsCollector

logger = structlog.get_logger(__name__)


class AuthService:
    """
    Consolidated service for authentication, authorization, and security.
    Handles: login/logout, permissions, session management, security validation.
    """
    
    def __init__(
        self,
        authenticate_handler: AuthenticateUserCommandHandler,
        auth_settings: AuthSettings,
        metrics_collector: Optional[MetricsCollector] = None
    ):
        self.authenticate_handler = authenticate_handler
        self.auth_settings = auth_settings
        self.metrics_collector = metrics_collector

    # === AUTHENTICATION ===
    
    async def authenticate_user(
        self, 
        email: str, 
        password: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """Authenticate user and return token."""
        start_time = datetime.now()
        
        try:
            command = AuthenticateUserCommand(
                email=email,
                password=password,
                client_ip=client_ip,
                user_agent=user_agent
            )
            
            result = await self.authenticate_handler.handle(command)
            
            # Record success metrics
            if self.metrics_collector and result.get("success"):
                self._record_auth_success(email, start_time)
            elif self.metrics_collector:
                self._record_auth_failure(email, "invalid_credentials", start_time)
                
            return result
            
        except Exception as e:
            if self.metrics_collector:
                self._record_auth_failure(email, "system_error", start_time)
            
            logger.error("authentication.failed", email=email, error=str(e))
            return {
                "success": False,
                "token": None,
                "user": None,
                "message": "Authentication failed"
            }
    
    async def logout_user(self, user_id: UUID, token: str) -> Dict[str, Any]:
        """Logout user and invalidate token."""
        try:
            # Implementation for token invalidation
            # This would typically involve blacklisting the token
            
            logger.info("user.logged_out", user_id=str(user_id))
            
            return {
                "success": True,
                "message": "Logged out successfully"
            }
            
        except Exception as e:
            logger.error("logout.failed", user_id=str(user_id), error=str(e))
            return {
                "success": False,
                "message": "Logout failed"
            }

    # === AUTHORIZATION & PERMISSIONS ===
    
    def can_user_access_resource(self, user: User, resource: str, action: str) -> bool:
        """Check if user can perform action on resource."""
        # Admin can do everything
        if user.role == UserRole.ADMIN:
            return True
        
        # Check specific permissions based on resource and action
        return self._check_permission(user.role, resource, action)
    
    def require_admin_role(self, user: User) -> None:
        """Require user to have admin role."""
        if user.role != UserRole.ADMIN:
            raise PermissionError("Admin role required")
    
    def require_role(self, user: User, required_role: UserRole) -> None:
        """Require user to have specific role."""
        if user.role != required_role:
            raise PermissionError(f"Role {required_role.value} required")
    
    def can_modify_user(self, current_user: User, target_user_id: UUID) -> bool:
        """Check if current user can modify target user."""
        # Admin can modify anyone
        if current_user.role == UserRole.ADMIN:
            return True
        
        # Users can only modify themselves
        return str(current_user.id) == str(target_user_id)
    
    def can_access_media(self, user: User, media_owner_id: UUID) -> bool:
        """Check if user can access media."""
        # Admin can access all media
        if user.role == UserRole.ADMIN:
            return True
        
        # Users can only access their own media
        return str(user.id) == str(media_owner_id)

    # === SECURITY VALIDATION ===
    
    def validate_session(self, user: User, client_ip: str, user_agent: str) -> bool:
        """Validate user session for security."""
        try:
            # Basic session validation
            # In production, this would include more sophisticated checks
            
            # Check if account is active
            if not self._is_account_active(user):
                return False
            
            # Additional security checks could be added here
            # - IP whitelist/blacklist
            # - Device fingerprinting
            # - Suspicious activity detection
            
            return True
            
        except Exception as e:
            logger.error("session.validation_failed", user_id=str(user.id), error=str(e))
            return False
    
    def detect_suspicious_activity(self, user: User, client_ip: str, action: str) -> bool:
        """Detect suspicious user activity."""
        # Implementation for suspicious activity detection
        # This could include:
        # - Multiple failed login attempts
        # - Login from unusual locations
        # - Unusual access patterns
        
        return False  # Placeholder
    
    def require_password_reset(self, user: User) -> bool:
        """Check if user should be required to reset password."""
        # Implementation for password reset requirements
        # This could be based on:
        # - Password age
        # - Security breaches
        # - Policy changes
        
        return False  # Placeholder

    # === PRIVATE METHODS ===
    
    def _check_permission(self, role: UserRole, resource: str, action: str) -> bool:
        """Check specific permission for role."""
        # Define permission matrix
        permissions = {
            UserRole.USER: {
                "media": ["read", "create", "update_own", "delete_own"],
                "transcription": ["read_own", "create_own"],
                "summary": ["read_own", "create_own"],
                "profile": ["read_own", "update_own"]
            },
            UserRole.ADMIN: {
                "*": ["*"]  # Admin has all permissions
            }
        }
        
        user_permissions = permissions.get(role, {})
        
        # Check wildcard permissions for admin
        if "*" in user_permissions and "*" in user_permissions["*"]:
            return True
        
        # Check specific resource permissions
        resource_permissions = user_permissions.get(resource, [])
        
        return action in resource_permissions or "*" in resource_permissions
    
    def _is_account_active(self, user: User) -> bool:
        """Check if user account is active."""
        # Implementation for account status check
        # This could check:
        # - Account suspension
        # - Email verification
        # - Terms acceptance
        
        return True  # Placeholder
    
    def _record_auth_success(self, email: str, start_time: datetime) -> None:
        """Record successful authentication metrics."""
        if not self.metrics_collector:
            return
            
        duration = (datetime.now() - start_time).total_seconds()
        
        self.metrics_collector.record_counter(
            "auth_attempts_total",
            labels={"status": "success", "method": "password"}
        )
        
        self.metrics_collector.record_histogram(
            "auth_duration_seconds",
            duration,
            labels={"status": "success"}
        )
    
    def _record_auth_failure(self, email: str, error_type: str, start_time: datetime) -> None:
        """Record failed authentication metrics."""
        if not self.metrics_collector:
            return
            
        duration = (datetime.now() - start_time).total_seconds()
        
        self.metrics_collector.record_counter(
            "auth_attempts_total",
            labels={"status": "failure", "error_type": error_type, "method": "password"}
        )
        
        self.metrics_collector.record_histogram(
            "auth_duration_seconds",
            duration,
            labels={"status": "failure"}
        )