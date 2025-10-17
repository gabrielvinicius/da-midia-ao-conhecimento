"""
Authentication Metrics Service - Single Responsibility: Metrics collection.
Follows SRP by handling only metrics-related operations for authentication.
"""
import time
from typing import Dict, Any
from uuid import UUID
from datetime import datetime, timedelta
import structlog

from src.auth.domain.interfaces import IAuthenticationMetricsService
from src.shared.monitoring.metrics_collector import MetricsCollector

logger = structlog.get_logger(__name__)


class AuthenticationMetricsService(IAuthenticationMetricsService):
    """
    Handles authentication metrics following SRP.
    Single responsibility: Collect and report authentication metrics.
    """
    
    def __init__(self, metrics_collector: MetricsCollector):
        self._metrics_collector = metrics_collector
        self._login_attempts = {}  # In-memory store for demo (use Redis in production)
    
    def record_login_attempt(self, email: str, success: bool, ip_address: str) -> None:
        """
        Record login attempt for metrics.
        
        Args:
            email: User email
            success: Whether login was successful
            ip_address: IP address of attempt
        """
        # Record counter metrics
        status = "success" if success else "failure"
        self._metrics_collector.record_counter(
            "auth_login_attempts_total",
            labels={"status": status, "ip": self._anonymize_ip(ip_address)}
        )
        
        # Track failed attempts for rate limiting
        if not success:
            self._track_failed_attempt(email, ip_address)
        else:
            self._clear_failed_attempts(email)
        
        logger.info(
            "auth.metrics.login_attempt",
            email=self._anonymize_email(email),
            success=success,
            ip_address=self._anonymize_ip(ip_address)
        )
    
    def record_token_generation(self, user_id: UUID, token_type: str) -> None:
        """
        Record token generation event.
        
        Args:
            user_id: User ID
            token_type: Type of token (access, refresh)
        """
        self._metrics_collector.record_counter(
            "auth_tokens_generated_total",
            labels={"token_type": token_type}
        )
        
        # Record token generation histogram (for rate analysis)
        self._metrics_collector.record_histogram(
            "auth_token_generation_timestamp",
            time.time(),
            labels={"token_type": token_type}
        )
        
        logger.debug(
            "auth.metrics.token_generated",
            user_id=str(user_id),
            token_type=token_type
        )
    
    def record_authentication_failure(self, email: str, reason: str, ip_address: str) -> None:
        """
        Record authentication failure.
        
        Args:
            email: User email
            reason: Failure reason
            ip_address: IP address
        """
        failure_category = self._categorize_failure_reason(reason)
        
        self._metrics_collector.record_counter(
            "auth_failures_total",
            labels={"reason": failure_category, "ip": self._anonymize_ip(ip_address)}
        )
        
        # Track security metrics
        self._metrics_collector.record_counter(
            "auth_security_events_total",
            labels={"event_type": "authentication_failure", "severity": self._get_failure_severity(reason)}
        )
        
        logger.warning(
            "auth.metrics.authentication_failure",
            email=self._anonymize_email(email),
            reason=reason,
            category=failure_category,
            ip_address=self._anonymize_ip(ip_address)
        )
    
    def get_authentication_stats(self, time_range: str) -> dict:
        """
        Get authentication statistics.
        
        Args:
            time_range: Time range for stats (hour, day, week)
            
        Returns:
            Dict with authentication statistics
        """
        # This would typically query stored metrics
        # For now, return basic structure with current data
        
        current_time = datetime.utcnow()
        
        stats = {
            "time_range": time_range,
            "generated_at": current_time.isoformat(),
            "summary": {
                "total_login_attempts": self._get_metric_count("auth_login_attempts_total"),
                "successful_logins": self._get_metric_count("auth_login_attempts_total", {"status": "success"}),
                "failed_logins": self._get_metric_count("auth_login_attempts_total", {"status": "failure"}),
                "tokens_generated": self._get_metric_count("auth_tokens_generated_total")
            },
            "failure_analysis": {
                "invalid_credentials": self._get_metric_count("auth_failures_total", {"reason": "invalid_credentials"}),
                "account_locked": self._get_metric_count("auth_failures_total", {"reason": "account_locked"}),
                "rate_limited": self._get_metric_count("auth_failures_total", {"reason": "rate_limited"}),
                "validation_error": self._get_metric_count("auth_failures_total", {"reason": "validation_error"})
            },
            "security_metrics": {
                "suspicious_activity_detected": self._get_suspicious_activity_count(),
                "unique_ips": self._get_unique_ip_count(),
                "security_events": self._get_metric_count("auth_security_events_total")
            },
            "performance_metrics": {
                "average_login_duration": self._calculate_average_login_duration(),
                "peak_login_hour": self._get_peak_login_hour(),
                "success_rate": self._calculate_success_rate()
            }
        }
        
        logger.info(
            "auth.metrics.stats_generated",
            time_range=time_range,
            total_attempts=stats["summary"]["total_login_attempts"]
        )
        
        return stats
    
    def get_user_login_patterns(self, user_id: UUID, days: int = 30) -> dict:
        """
        Get login patterns for a specific user.
        
        Args:
            user_id: User ID
            days: Number of days to analyze
            
        Returns:
            Dict with user login patterns
        """
        # This would analyze user-specific login data
        return {
            "user_id": str(user_id),
            "analysis_period_days": days,
            "total_logins": 0,  # Placeholder
            "average_logins_per_day": 0.0,
            "most_common_login_hours": [],
            "devices_used": [],
            "locations_detected": [],
            "security_score": 85.0  # Placeholder security score
        }
    
    def _track_failed_attempt(self, email: str, ip_address: str) -> None:
        """Track failed login attempt for rate limiting."""
        current_time = time.time()
        
        # Track by email
        if email not in self._login_attempts:
            self._login_attempts[email] = []
        self._login_attempts[email].append(current_time)
        
        # Keep only recent attempts (last hour)
        cutoff_time = current_time - 3600  # 1 hour
        self._login_attempts[email] = [
            attempt_time for attempt_time in self._login_attempts[email]
            if attempt_time > cutoff_time
        ]
    
    def _clear_failed_attempts(self, email: str) -> None:
        """Clear failed attempts after successful login."""
        if email in self._login_attempts:
            del self._login_attempts[email]
    
    def _categorize_failure_reason(self, reason: str) -> str:
        """Categorize failure reason for metrics."""
        reason_lower = reason.lower()
        
        if "password" in reason_lower or "credential" in reason_lower:
            return "invalid_credentials"
        elif "locked" in reason_lower or "suspended" in reason_lower:
            return "account_locked"
        elif "rate" in reason_lower or "limit" in reason_lower:
            return "rate_limited"
        elif "validation" in reason_lower or "format" in reason_lower:
            return "validation_error"
        elif "token" in reason_lower:
            return "token_error"
        else:
            return "unknown_error"
    
    def _get_failure_severity(self, reason: str) -> str:
        """Get severity level for failure."""
        if "rate" in reason.lower() or "suspicious" in reason.lower():
            return "high"
        elif "locked" in reason.lower():
            return "medium"
        else:
            return "low"
    
    def _anonymize_email(self, email: str) -> str:
        """Anonymize email for logging."""
        if "@" in email:
            local, domain = email.split("@", 1)
            return f"{local[:2]}***@{domain}"
        return "***"
    
    def _anonymize_ip(self, ip_address: str) -> str:
        """Anonymize IP address for logging."""
        if "." in ip_address:  # IPv4
            parts = ip_address.split(".")
            return f"{parts[0]}.{parts[1]}.***.***.***"
        elif ":" in ip_address:  # IPv6
            parts = ip_address.split(":")
            return f"{parts[0]}:{parts[1]}:***:***:***:***:***:***"
        return "***"
    
    def _get_metric_count(self, metric_name: str, labels: dict = None) -> int:
        """Get metric count (placeholder implementation)."""
        # In real implementation, this would query the metrics backend
        return 0
    
    def _get_suspicious_activity_count(self) -> int:
        """Get count of suspicious activities."""
        return len([email for email, attempts in self._login_attempts.items() if len(attempts) > 5])
    
    def _get_unique_ip_count(self) -> int:
        """Get count of unique IP addresses."""
        # Placeholder implementation
        return 0
    
    def _calculate_average_login_duration(self) -> float:
        """Calculate average login duration."""
        # Placeholder implementation
        return 1.5  # seconds
    
    def _get_peak_login_hour(self) -> int:
        """Get peak login hour."""
        # Placeholder implementation
        return 9  # 9 AM
    
    def _calculate_success_rate(self) -> float:
        """Calculate overall success rate."""
        total = self._get_metric_count("auth_login_attempts_total")
        successful = self._get_metric_count("auth_login_attempts_total", {"status": "success"})
        
        if total == 0:
            return 100.0
        
        return round((successful / total) * 100, 2)