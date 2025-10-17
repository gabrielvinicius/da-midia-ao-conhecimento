"""
Enhanced Authentication Service following SOLID principles.
Single Responsibility: Handle core authentication orchestration with validation and monitoring.
"""
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import structlog

from src.auth.application.commands.commands import AuthenticateUserCommand
from src.auth.application.commands.handlers import AuthenticateUserCommandHandler
from src.auth.domain.interfaces import (
    IEnhancedAuthenticationService,
    IAuthenticationValidator,
    IAuthenticationMetricsService,
    IUserSessionService,
    IUserSecurityService,
    ITokenService
)

logger = structlog.get_logger(__name__)


class EnhancedAuthenticationService(IEnhancedAuthenticationService):
    """
    Enhanced authentication service following SOLID principles.
    
    Single Responsibility: Orchestrate authentication workflow with validation and security.
    Open/Closed: Extensible through service injection.
    Liskov Substitution: Implements IEnhancedAuthenticationService contract.
    Interface Segregation: Uses specific interfaces for each concern.
    Dependency Inversion: Depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        authenticate_handler: AuthenticateUserCommandHandler,
        validator: IAuthenticationValidator,
        metrics_service: IAuthenticationMetricsService,
        session_service: IUserSessionService,
        security_service: IUserSecurityService,
        token_service: ITokenService
    ):
        self._authenticate_handler = authenticate_handler
        self._validator = validator
        self._metrics_service = metrics_service
        self._session_service = session_service
        self._security_service = security_service
        self._token_service = token_service
    
    async def authenticate_with_validation(
        self, 
        email: str, 
        password: str, 
        ip_address: str,
        user_agent: str
    ) -> dict:
        """
        Authenticate user with comprehensive validation.
        
        Args:
            email: User email
            password: User password
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Dict with authentication result and session info
        """
        try:
            # Validate input format
            self._validator.validate_login_credentials(email, password)
            
            # Check rate limiting
            if not await self._security_service.enforce_rate_limiting(ip_address, "login"):
                self._metrics_service.record_authentication_failure(
                    email, "Rate limit exceeded", ip_address
                )
                raise ValidationError("Too many login attempts. Please try again later.")
            
            # Record login attempt start
            self._metrics_service.record_login_attempt(email, False, ip_address)
            
            # Perform authentication
            command = AuthenticateUserCommand(email=email, password=password)
            auth_result = await self._authenticate_handler.handle(command)
            
            user_id = UUID(auth_result["user"]["id"])
            
            # Detect suspicious activity
            activity_data = {
                "ip_address": ip_address,
                "user_agent": user_agent,
                "login_time": datetime.utcnow().isoformat()
            }
            
            suspicious = await self._security_service.detect_suspicious_activity(user_id, activity_data)
            if suspicious:
                await self._security_service.log_security_event(
                    user_id, "suspicious_login", activity_data
                )
            
            # Create session
            session_metadata = {
                "ip_address": ip_address,
                "user_agent": user_agent,
                "login_time": datetime.utcnow().isoformat(),
                "suspicious": suspicious
            }
            
            session_id = await self._session_service.create_session(
                user_id, auth_result["access_token"], session_metadata
            )
            
            # Record successful metrics
            self._metrics_service.record_login_attempt(email, True, ip_address)
            self._metrics_service.record_token_generation(user_id, "access")
            
            # Enhanced response with session info
            enhanced_result = {
                **auth_result,
                "session_id": session_id,
                "security_flags": {
                    "suspicious_activity": suspicious,
                    "new_device": True  # Placeholder - would check device fingerprint
                }
            }
            
            logger.info(
                "auth.authentication.success",
                user_id=str(user_id),
                email=email,
                ip_address=ip_address,
                suspicious=suspicious
            )
            
            return enhanced_result
            
        except Exception as e:
            # Record failure metrics
            self._metrics_service.record_authentication_failure(email, str(e), ip_address)
            
            logger.error(
                "auth.authentication.failed",
                email=email,
                ip_address=ip_address,
                error=str(e)
            )
            raise
    
    async def validate_and_refresh_token(self, refresh_token: str) -> dict:
        """
        Validate and refresh authentication token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            Dict with new token information
        """
        try:
            # Validate refresh token format
            self._validator.validate_refresh_token(refresh_token)
            
            # Verify and decode refresh token
            token_data = self._token_service.verify_token(refresh_token)
            user_id = UUID(token_data["sub"])
            
            # Create new access token
            new_access_token = self._token_service.create_access_token({
                "sub": str(user_id),
                "type": "access"
            })
            
            # Record token generation
            self._metrics_service.record_token_generation(user_id, "access")
            
            logger.info(
                "auth.token.refreshed",
                user_id=str(user_id)
            )
            
            return {
                "access_token": new_access_token,
                "token_type": "bearer",
                "expires_in": 3600  # 1 hour
            }
            
        except Exception as e:
            logger.error(
                "auth.token.refresh_failed",
                error=str(e)
            )
            raise
    
    async def logout_user(self, user_id: UUID, session_id: str) -> None:
        """
        Logout user and invalidate session.
        
        Args:
            user_id: User ID
            session_id: Session ID to invalidate
        """
        try:
            # Invalidate session
            await self._session_service.invalidate_session(session_id)
            
            logger.info(
                "auth.logout.success",
                user_id=str(user_id),
                session_id=session_id
            )
            
        except Exception as e:
            logger.error(
                "auth.logout.failed",
                user_id=str(user_id),
                session_id=session_id,
                error=str(e)
            )
            raise
    
    async def logout_all_sessions(self, user_id: UUID) -> int:
        """
        Logout user from all sessions.
        
        Args:
            user_id: User ID
            
        Returns:
            int: Number of sessions invalidated
        """
        try:
            invalidated_count = await self._session_service.invalidate_all_user_sessions(user_id)
            
            logger.info(
                "auth.logout_all.success",
                user_id=str(user_id),
                sessions_invalidated=invalidated_count
            )
            
            return invalidated_count
            
        except Exception as e:
            logger.error(
                "auth.logout_all.failed",
                user_id=str(user_id),
                error=str(e)
            )
            raise


class AuthenticationService:
    """
    Legacy authentication service (maintained for backward compatibility).
    
    Single Responsibility: Handle user login/authentication flows.
    """
    
    def __init__(self, authenticate_handler: AuthenticateUserCommandHandler):
        self.authenticate_handler = authenticate_handler
    
    async def authenticate(self, email: str, password: str) -> dict:
        """
        Authenticate a user with email and password.
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            dict: Authentication result with token information
            
        Raises:
            ValueError: If credentials are invalid
        """
        command = AuthenticateUserCommand(email=email, password=password)
        return await self.authenticate_handler.handle(command)
    
    async def validate_token(self, token: str) -> bool:
        """
        Validate if a token is valid and not expired.
        
        Args:
            token: JWT token to validate
            
        Returns:
            bool: True if token is valid, False otherwise
        """
        # This would use JWT provider for validation
        # Implementation depends on JWT provider setup
        pass
    
    async def refresh_token(self, refresh_token: str) -> dict:
        """
        Refresh an authentication token.
        
        Args:
            refresh_token: Refresh token
            
        Returns:
            dict: New token information
        """
        # Implementation for token refresh
        pass