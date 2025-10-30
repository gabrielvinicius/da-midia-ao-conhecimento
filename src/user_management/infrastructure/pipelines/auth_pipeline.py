"""
Authentication and Authorization pipeline using Chain of Responsibility Pattern
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from uuid import UUID
import time
import hashlib

from src.shared.patterns.chain_of_responsibility import (
    ValidationHandler, TransformationHandler, FilterHandler,
    ProcessingContext, HandlerResult, ChainBuilder, ProcessingPipeline
)


class AuthAction(str, Enum):
    """Authentication/Authorization actions"""
    LOGIN = "login"
    LOGOUT = "logout"
    REGISTER = "register"
    REFRESH_TOKEN = "refresh_token"
    RESET_PASSWORD = "reset_password"
    CHANGE_PASSWORD = "change_password"
    ACCESS_RESOURCE = "access_resource"


@dataclass
class AuthRequest:
    """Request object for authentication pipeline"""
    action: AuthAction
    user_id: Optional[UUID] = None
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None
    resource: Optional[str] = None
    permissions_required: List[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.permissions_required is None:
            self.permissions_required = []
        if self.metadata is None:
            self.metadata = {}


class RateLimitValidationHandler(ValidationHandler):
    """Rate limiting for authentication attempts"""
    
    def __init__(self, max_attempts: int = 5, window_minutes: int = 15):
        super().__init__("RateLimitValidator")
        self.max_attempts = max_attempts
        self.window_seconds = window_minutes * 60
        self.attempts = {}  # In production, use Redis or database
    
    async def validate(self, context: ProcessingContext) -> bool:
        """Validate rate limits"""
        request: AuthRequest = context.request
        
        # Skip rate limiting for some actions
        if request.action in [AuthAction.LOGOUT, AuthAction.ACCESS_RESOURCE]:
            return True
        
        # Create key for rate limiting
        rate_limit_key = self._get_rate_limit_key(request)
        current_time = time.time()
        
        # Clean old attempts
        self._cleanup_old_attempts(current_time)
        
        # Check current attempts
        user_attempts = self.attempts.get(rate_limit_key, [])
        recent_attempts = [
            attempt_time for attempt_time in user_attempts
            if current_time - attempt_time < self.window_seconds
        ]
        
        if len(recent_attempts) >= self.max_attempts:
            context.add_error(
                f"Rate limit exceeded. Max {self.max_attempts} attempts "
                f"per {self.window_seconds // 60} minutes"
            )
            context.add_metadata("rate_limited", True)
            return False
        
        # Record this attempt
        recent_attempts.append(current_time)
        self.attempts[rate_limit_key] = recent_attempts
        
        context.add_metadata("rate_limit_attempts", len(recent_attempts))
        return True
    
    def _get_rate_limit_key(self, request: AuthRequest) -> str:
        """Generate rate limit key"""
        if request.username:
            return f"username:{request.username}"
        elif request.email:
            return f"email:{request.email}"
        elif request.client_ip:
            return f"ip:{request.client_ip}"
        else:
            return "anonymous"
    
    def _cleanup_old_attempts(self, current_time: float):
        """Remove old attempts to prevent memory leak"""
        for key in list(self.attempts.keys()):
            self.attempts[key] = [
                attempt_time for attempt_time in self.attempts[key]
                if current_time - attempt_time < self.window_seconds
            ]
            if not self.attempts[key]:
                del self.attempts[key]


class InputValidationHandler(ValidationHandler):
    """Validate input parameters for auth requests"""
    
    def __init__(self):
        super().__init__("InputValidator")
    
    async def validate(self, context: ProcessingContext) -> bool:
        """Validate required inputs"""
        request: AuthRequest = context.request
        
        # Validate based on action
        if request.action == AuthAction.LOGIN:
            if not (request.username or request.email) or not request.password:
                context.add_error("Username/email and password are required for login")
                return False
        
        elif request.action == AuthAction.REGISTER:
            if not request.username or not request.email or not request.password:
                context.add_error("Username, email, and password are required for registration")
                return False
            
            # Validate email format
            if not self._is_valid_email(request.email):
                context.add_error("Invalid email format")
                return False
        
        elif request.action == AuthAction.REFRESH_TOKEN:
            if not request.token:
                context.add_error("Token is required for refresh")
                return False
        
        elif request.action == AuthAction.ACCESS_RESOURCE:
            if not request.user_id or not request.resource:
                context.add_error("User ID and resource are required for access check")
                return False
        
        elif request.action == AuthAction.CHANGE_PASSWORD:
            if not request.user_id or not request.password:
                context.add_error("User ID and new password are required")
                return False
        
        context.add_metadata("input_validation", "passed")
        return True
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None


class PasswordStrengthValidationHandler(ValidationHandler):
    """Validate password strength"""
    
    def __init__(self, min_length: int = 8):
        super().__init__("PasswordValidator")
        self.min_length = min_length
    
    async def validate(self, context: ProcessingContext) -> bool:
        """Validate password strength"""
        request: AuthRequest = context.request
        
        # Only validate for actions that set passwords
        if request.action not in [AuthAction.REGISTER, AuthAction.CHANGE_PASSWORD]:
            return True
        
        if not request.password:
            return True  # Will be caught by input validation
        
        password = request.password
        errors = []
        
        # Length check
        if len(password) < self.min_length:
            errors.append(f"Password must be at least {self.min_length} characters")
        
        # Character type checks
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        if errors:
            for error in errors:
                context.add_error(error)
            return False
        
        context.add_metadata("password_strength", "strong")
        return True


class SecurityChecksHandler(ValidationHandler):
    """Security validation checks"""
    
    def __init__(self, security_service=None):
        super().__init__("SecurityValidator")
        self.security_service = security_service
        self.suspicious_patterns = [
            "admin", "root", "test", "guest", "anonymous",
            "password", "123456", "qwerty"
        ]
    
    async def validate(self, context: ProcessingContext) -> bool:
        """Perform security checks"""
        request: AuthRequest = context.request
        
        # Check for suspicious usernames
        if request.username and request.username.lower() in self.suspicious_patterns:
            context.add_error(f"Username '{request.username}' is not allowed")
            return False
        
        # Check for common weak passwords
        if request.password and request.password.lower() in self.suspicious_patterns:
            context.add_error("Password is too common and not allowed")
            return False
        
        # Check for SQL injection attempts
        if self._contains_sql_injection(request):
            context.add_error("Suspicious input detected")
            context.add_metadata("security_alert", "sql_injection_attempt")
            return False
        
        # IP-based security checks
        if self.security_service and request.client_ip:
            try:
                is_blocked = await self.security_service.is_ip_blocked(request.client_ip)
                if is_blocked:
                    context.add_error("Access denied from this IP address")
                    return False
            except Exception as e:
                context.add_metadata("security_check_error", str(e))
        
        context.add_metadata("security_checks", "passed")
        return True
    
    def _contains_sql_injection(self, request: AuthRequest) -> bool:
        """Basic SQL injection detection"""
        sql_patterns = [
            "union select", "drop table", "insert into", "delete from",
            "update set", "create table", "alter table", "--", "/*", "*/"
        ]
        
        fields_to_check = [request.username, request.email, request.password]
        for field in fields_to_check:
            if field:
                field_lower = field.lower()
                if any(pattern in field_lower for pattern in sql_patterns):
                    return True
        return False


class UserLookupHandler(TransformationHandler):
    """Look up user information"""
    
    def __init__(self, user_service=None):
        super().__init__("UserLookup")
        self.user_service = user_service
    
    async def transform(self, context: ProcessingContext) -> None:
        """Look up user information"""
        request: AuthRequest = context.request
        
        if not self.user_service:
            context.add_metadata("user_lookup", "service_not_available")
            return
        
        try:
            user = None
            
            # Look up user based on available identifiers
            if request.user_id:
                user = await self.user_service.get_by_id(request.user_id)
            elif request.username:
                user = await self.user_service.get_by_username(request.username)
            elif request.email:
                user = await self.user_service.get_by_email(request.email)
            
            if user:
                context.add_metadata("user_found", True)
                context.add_metadata("user_info", {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "is_active": user.is_active,
                    "roles": user.roles if hasattr(user, 'roles') else []
                })
            else:
                context.add_metadata("user_found", False)
                
        except Exception as e:
            context.add_metadata("user_lookup_error", str(e))


class PasswordVerificationHandler(ValidationHandler):
    """Verify password for login attempts"""
    
    def __init__(self, password_service=None):
        super().__init__("PasswordVerification")
        self.password_service = password_service
    
    async def validate(self, context: ProcessingContext) -> bool:
        """Verify password"""
        request: AuthRequest = context.request
        
        # Only for login attempts
        if request.action != AuthAction.LOGIN:
            return True
        
        user_info = context.metadata.get("user_info")
        if not user_info:
            context.add_error("User not found")
            return False
        
        if not user_info.get("is_active", False):
            context.add_error("User account is inactive")
            return False
        
        if not self.password_service:
            context.add_error("Password verification service not available")
            return False
        
        try:
            is_valid = await self.password_service.verify_password(
                request.password,
                user_info["id"]
            )
            
            if not is_valid:
                context.add_error("Invalid password")
                context.add_metadata("password_verification", "failed")
                return False
            
            context.add_metadata("password_verification", "passed")
            return True
            
        except Exception as e:
            context.add_error(f"Password verification failed: {str(e)}")
            return False


class PermissionCheckHandler(ValidationHandler):
    """Check user permissions for resource access"""
    
    def __init__(self, permission_service=None):
        super().__init__("PermissionCheck")
        self.permission_service = permission_service
    
    async def validate(self, context: ProcessingContext) -> bool:
        """Check permissions"""
        request: AuthRequest = context.request
        
        # Only for resource access
        if request.action != AuthAction.ACCESS_RESOURCE:
            return True
        
        user_info = context.metadata.get("user_info")
        if not user_info:
            context.add_error("User information not available")
            return False
        
        if not self.permission_service:
            context.add_error("Permission service not available")
            return False
        
        try:
            has_permission = await self.permission_service.check_permission(
                user_info["id"],
                request.resource,
                request.permissions_required
            )
            
            if not has_permission:
                context.add_error(
                    f"User does not have required permissions for resource: {request.resource}"
                )
                context.add_metadata("permission_check", "denied")
                return False
            
            context.add_metadata("permission_check", "granted")
            return True
            
        except Exception as e:
            context.add_error(f"Permission check failed: {str(e)}")
            return False


class TokenGenerationHandler(TransformationHandler):
    """Generate authentication tokens"""
    
    def __init__(self, token_service=None):
        super().__init__("TokenGeneration")
        self.token_service = token_service
    
    async def transform(self, context: ProcessingContext) -> None:
        """Generate tokens for successful authentication"""
        request: AuthRequest = context.request
        
        # Only generate tokens for login and refresh
        if request.action not in [AuthAction.LOGIN, AuthAction.REFRESH_TOKEN]:
            return
        
        user_info = context.metadata.get("user_info")
        if not user_info or not self.token_service:
            return
        
        try:
            if request.action == AuthAction.LOGIN:
                tokens = await self.token_service.generate_tokens(user_info["id"])
            else:  # REFRESH_TOKEN
                tokens = await self.token_service.refresh_tokens(request.token)
            
            context.add_metadata("tokens", tokens)
            context.add_metadata("token_generation", "success")
            
        except Exception as e:
            context.add_metadata("token_generation_error", str(e))


class AuditLoggingHandler(TransformationHandler):
    """Log authentication events for audit"""
    
    def __init__(self, audit_service=None):
        super().__init__("AuditLogging")
        self.audit_service = audit_service
    
    async def transform(self, context: ProcessingContext) -> None:
        """Log audit events"""
        request: AuthRequest = context.request
        
        audit_event = {
            "action": request.action.value,
            "user_id": request.user_id,
            "username": request.username,
            "client_ip": request.client_ip,
            "user_agent": request.user_agent,
            "success": not context.has_errors(),
            "timestamp": time.time(),
            "errors": context.errors if context.has_errors() else None
        }
        
        if self.audit_service:
            try:
                await self.audit_service.log_event(audit_event)
                context.add_metadata("audit_logged", True)
            except Exception as e:
                context.add_metadata("audit_log_error", str(e))
        else:
            context.add_metadata("audit_logged", False)


class AuthPipelineFactory:
    """Factory for creating authentication pipelines"""
    
    @staticmethod
    def create_login_pipeline(
        user_service=None,
        password_service=None,
        token_service=None,
        audit_service=None,
        security_service=None
    ) -> ProcessingPipeline:
        """Create login pipeline"""
        
        chain = (ChainBuilder("LoginPipeline")
                .add_validation(RateLimitValidationHandler())
                .add_validation(InputValidationHandler())
                .add_validation(SecurityChecksHandler(security_service))
                .add_transformation(UserLookupHandler(user_service))
                .add_validation(PasswordVerificationHandler(password_service))
                .add_transformation(TokenGenerationHandler(token_service))
                .add_transformation(AuditLoggingHandler(audit_service))
                .build())
        
        return ProcessingPipeline("LoginPipeline", chain)
    
    @staticmethod
    def create_registration_pipeline(
        user_service=None,
        audit_service=None,
        security_service=None
    ) -> ProcessingPipeline:
        """Create registration pipeline"""
        
        chain = (ChainBuilder("RegistrationPipeline")
                .add_validation(RateLimitValidationHandler())
                .add_validation(InputValidationHandler())
                .add_validation(PasswordStrengthValidationHandler())
                .add_validation(SecurityChecksHandler(security_service))
                .add_transformation(UserLookupHandler(user_service))  # Check if user exists
                .add_transformation(AuditLoggingHandler(audit_service))
                .build())
        
        return ProcessingPipeline("RegistrationPipeline", chain)
    
    @staticmethod
    def create_authorization_pipeline(
        user_service=None,
        permission_service=None,
        audit_service=None
    ) -> ProcessingPipeline:
        """Create authorization pipeline"""
        
        chain = (ChainBuilder("AuthorizationPipeline")
                .add_validation(InputValidationHandler())
                .add_transformation(UserLookupHandler(user_service))
                .add_validation(PermissionCheckHandler(permission_service))
                .add_transformation(AuditLoggingHandler(audit_service))
                .build())
        
        return ProcessingPipeline("AuthorizationPipeline", chain)


def register_auth_pipelines():
    """Register authentication pipelines"""
    from src.shared.patterns.chain_of_responsibility import PipelineRegistry
    
    # Login pipeline
    login_pipeline = AuthPipelineFactory.create_login_pipeline()
    PipelineRegistry.register_pipeline("auth_login", login_pipeline)
    
    # Registration pipeline
    registration_pipeline = AuthPipelineFactory.create_registration_pipeline()
    PipelineRegistry.register_pipeline("auth_registration", registration_pipeline)
    
    # Authorization pipeline
    authorization_pipeline = AuthPipelineFactory.create_authorization_pipeline()
    PipelineRegistry.register_pipeline("auth_authorization", authorization_pipeline)