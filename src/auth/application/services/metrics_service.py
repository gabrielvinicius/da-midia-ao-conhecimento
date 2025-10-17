"""
Consolidated Auth Metrics Service
Consolidates: AuthenticationMetricsService, AuthenticationValidator
"""
import structlog
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID

from src.shared.monitoring.metrics_collector import MetricsCollector

logger = structlog.get_logger(__name__)


class AuthMetricsService:
    """
    Consolidated service for all auth-related metrics and monitoring.
    Handles authentication metrics, validation tracking, and security monitoring.
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        self.metrics_collector = metrics_collector
        self._failed_attempts: Dict[str, int] = {}
        self._last_attempt: Dict[str, datetime] = {}

    # === AUTHENTICATION METRICS ===
    
    def record_login_attempt(self, email: str, success: bool, duration: float, client_ip: Optional[str] = None) -> None:
        """Record login attempt metrics."""
        status = "success" if success else "failure"
        
        self.metrics_collector.record_counter(
            "auth_login_attempts_total",
            labels={
                "status": status,
                "method": "password"
            }
        )
        
        self.metrics_collector.record_histogram(
            "auth_login_duration_seconds",
            duration,
            labels={"status": status}
        )
        
        if success:
            self._reset_failed_attempts(email)
            logger.info("auth.login.success", email=email, duration=duration)
        else:
            self._track_failed_attempt(email)
            logger.warning("auth.login.failure", email=email, duration=duration)
    
    def record_logout(self, user_id: UUID) -> None:
        """Record logout metrics."""
        self.metrics_collector.record_counter(
            "auth_logout_total",
            labels={"method": "manual"}
        )
        
        logger.info("auth.logout", user_id=str(user_id))
    
    def record_token_validation(self, success: bool, token_age: Optional[float] = None) -> None:
        """Record token validation metrics."""
        status = "success" if success else "failure"
        
        self.metrics_collector.record_counter(
            "auth_token_validations_total",
            labels={"status": status}
        )
        
        if token_age is not None:
            self.metrics_collector.record_histogram(
                "auth_token_age_seconds",
                token_age,
                labels={"status": status}
            )

    # === PASSWORD METRICS ===
    
    def record_password_change(self, user_id: UUID, success: bool, reason: str = "user_request") -> None:
        """Record password change metrics."""
        status = "success" if success else "failure"
        
        self.metrics_collector.record_counter(
            "auth_password_changes_total",
            labels={
                "status": status,
                "reason": reason
            }
        )
        
        logger.info("auth.password.change", user_id=str(user_id), success=success, reason=reason)
    
    def record_password_reset_request(self, email: str) -> None:
        """Record password reset request."""
        self.metrics_collector.record_counter(
            "auth_password_reset_requests_total"
        )
        
        logger.info("auth.password.reset_requested", email=email)
    
    def record_password_strength_check(self, strength_score: int) -> None:
        """Record password strength metrics."""
        self.metrics_collector.record_histogram(
            "auth_password_strength_score",
            strength_score,
            labels={"score_range": self._get_strength_range(strength_score)}
        )

    # === SECURITY METRICS ===
    
    def record_suspicious_activity(self, user_id: UUID, activity_type: str, risk_level: str) -> None:
        """Record suspicious activity detection."""
        self.metrics_collector.record_counter(
            "auth_suspicious_activity_total",
            labels={
                "activity_type": activity_type,
                "risk_level": risk_level
            }
        )
        
        logger.warning(
            "auth.security.suspicious_activity",
            user_id=str(user_id),
            activity_type=activity_type,
            risk_level=risk_level
        )
    
    def record_session_validation(self, success: bool, validation_type: str) -> None:
        """Record session validation metrics."""
        status = "success" if success else "failure"
        
        self.metrics_collector.record_counter(
            "auth_session_validations_total",
            labels={
                "status": status,
                "type": validation_type
            }
        )
    
    def record_rate_limit_hit(self, client_ip: str, endpoint: str) -> None:
        """Record rate limiting metrics."""
        self.metrics_collector.record_counter(
            "auth_rate_limit_hits_total",
            labels={"endpoint": endpoint}
        )
        
        logger.warning("auth.rate_limit.hit", client_ip=client_ip, endpoint=endpoint)

    # === USER METRICS ===
    
    def record_user_creation(self, success: bool, registration_method: str = "email") -> None:
        """Record user creation metrics."""
        status = "success" if success else "failure"
        
        self.metrics_collector.record_counter(
            "auth_user_registrations_total",
            labels={
                "status": status,
                "method": registration_method
            }
        )
    
    def record_user_role_change(self, from_role: str, to_role: str, admin_user_id: UUID) -> None:
        """Record user role change metrics."""
        self.metrics_collector.record_counter(
            "auth_role_changes_total",
            labels={
                "from_role": from_role,
                "to_role": to_role
            }
        )
        
        logger.info(
            "auth.user.role_changed",
            from_role=from_role,
            to_role=to_role,
            admin_user_id=str(admin_user_id)
        )

    # === VALIDATION METHODS ===
    
    def is_rate_limited(self, identifier: str, max_attempts: int = 5, window_minutes: int = 15) -> bool:
        """Check if identifier (email/IP) is rate limited."""
        now = datetime.now()
        
        # Clean old entries
        self._cleanup_old_attempts(window_minutes)
        
        # Check failed attempts in window
        failed_count = self._failed_attempts.get(identifier, 0)
        last_attempt = self._last_attempt.get(identifier)
        
        if last_attempt and now - last_attempt < timedelta(minutes=window_minutes):
            if failed_count >= max_attempts:
                self.record_rate_limit_hit(identifier, "auth")
                return True
        
        return False
    
    def validate_authentication_context(self, email: str, client_ip: str, user_agent: str) -> Dict[str, Any]:
        """Validate authentication context and return risk assessment."""
        risk_factors = []
        risk_score = 0
        
        # Check for rate limiting
        if self.is_rate_limited(email):
            risk_factors.append("rate_limited")
            risk_score += 50
        
        # Check for suspicious patterns
        if self._is_suspicious_ip(client_ip):
            risk_factors.append("suspicious_ip")
            risk_score += 30
        
        if self._is_suspicious_user_agent(user_agent):
            risk_factors.append("suspicious_user_agent")
            risk_score += 20
        
        # Determine risk level
        if risk_score >= 70:
            risk_level = "high"
        elif risk_score >= 40:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        return {
            "risk_level": risk_level,
            "risk_score": risk_score,
            "risk_factors": risk_factors,
            "allow_attempt": risk_score < 80
        }

    # === PRIVATE METHODS ===
    
    def _track_failed_attempt(self, identifier: str) -> None:
        """Track failed authentication attempt."""
        self._failed_attempts[identifier] = self._failed_attempts.get(identifier, 0) + 1
        self._last_attempt[identifier] = datetime.now()
    
    def _reset_failed_attempts(self, identifier: str) -> None:
        """Reset failed attempts counter for identifier."""
        self._failed_attempts.pop(identifier, None)
        self._last_attempt.pop(identifier, None)
    
    def _cleanup_old_attempts(self, window_minutes: int) -> None:
        """Clean up old failed attempt records."""
        cutoff = datetime.now() - timedelta(minutes=window_minutes)
        
        expired_keys = [
            key for key, timestamp in self._last_attempt.items()
            if timestamp < cutoff
        ]
        
        for key in expired_keys:
            self._failed_attempts.pop(key, None)
            self._last_attempt.pop(key, None)
    
    def _get_strength_range(self, score: int) -> str:
        """Get password strength range label."""
        if score >= 80:
            return "strong"
        elif score >= 60:
            return "medium"
        elif score >= 40:
            return "weak"
        else:
            return "very_weak"
    
    def _is_suspicious_ip(self, client_ip: str) -> bool:
        """Check if IP address is suspicious."""
        # Implementation for IP reputation checking
        # This could include checking against:
        # - Known malicious IP lists
        # - Tor exit nodes
        # - VPN/proxy detection
        # - Geolocation anomalies
        
        return False  # Placeholder
    
    def _is_suspicious_user_agent(self, user_agent: str) -> bool:
        """Check if user agent is suspicious."""
        # Implementation for user agent analysis
        # This could include checking for:
        # - Known bot signatures
        # - Unusual or malformed user agents
        # - Automated tool patterns
        
        return False  # Placeholder