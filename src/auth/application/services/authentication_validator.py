"""
Authentication Validator Service - Single Responsibility: Validation operations.
Follows SRP by handling only validation concerns for authentication.
"""
import re
from typing import Optional
import structlog

from src.auth.domain.interfaces import IAuthenticationValidator
from src.shared.exceptions.domain_exceptions import ValidationError

logger = structlog.get_logger(__name__)


class AuthenticationValidator(IAuthenticationValidator):
    """
    Validates authentication inputs and tokens following SRP.
    Single responsibility: All validation logic for authentication operations.
    """
    
    def __init__(self):
        self.email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        self.min_password_length = 8
        self.max_password_length = 128
    
    def validate_login_credentials(self, email: str, password: str) -> None:
        """
        Validate login credentials format.
        
        Args:
            email: Email address to validate
            password: Password to validate
            
        Raises:
            ValidationError: If credentials format is invalid
        """
        if not email or not email.strip():
            raise ValidationError("Email address is required")
        
        if not password:
            raise ValidationError("Password is required")
        
        # Validate email format
        self._validate_email_format(email.strip().lower())
        
        # Validate password format
        self._validate_password_format(password)
        
        logger.debug(
            "auth.validation.credentials_validated",
            email=email.strip().lower()
        )
    
    def validate_token_format(self, token: str) -> None:
        """
        Validate token format.
        
        Args:
            token: Token to validate
            
        Raises:
            ValidationError: If token format is invalid
        """
        if not token or not token.strip():
            raise ValidationError("Token is required")
        
        token = token.strip()
        
        # Basic JWT format validation (header.payload.signature)
        parts = token.split('.')
        if len(parts) != 3:
            raise ValidationError("Invalid token format")
        
        # Check for reasonable token length
        if len(token) < 50 or len(token) > 2000:
            raise ValidationError("Invalid token length")
        
        # Basic base64url character validation for JWT parts
        for part in parts:
            if not self._is_valid_base64url(part):
                raise ValidationError("Invalid token encoding")
        
        logger.debug(
            "auth.validation.token_validated",
            token_length=len(token)
        )
    
    def validate_refresh_token(self, refresh_token: str) -> None:
        """
        Validate refresh token.
        
        Args:
            refresh_token: Refresh token to validate
            
        Raises:
            ValidationError: If refresh token is invalid
        """
        if not refresh_token or not refresh_token.strip():
            raise ValidationError("Refresh token is required")
        
        refresh_token = refresh_token.strip()
        
        # Validate as JWT token
        self.validate_token_format(refresh_token)
        
        # Additional refresh token specific validation could go here
        # (e.g., checking token type claims)
        
        logger.debug(
            "auth.validation.refresh_token_validated",
            token_length=len(refresh_token)
        )
    
    def validate_registration_data(self, email: str, password: str, full_name: Optional[str] = None) -> None:
        """
        Validate user registration data.
        
        Args:
            email: Email address
            password: Password
            full_name: Optional full name
            
        Raises:
            ValidationError: If registration data is invalid
        """
        # Validate email
        if not email or not email.strip():
            raise ValidationError("Email address is required")
        
        self._validate_email_format(email.strip().lower())
        
        # Validate password strength
        self._validate_password_strength(password)
        
        # Validate full name if provided
        if full_name is not None:
            self._validate_full_name(full_name)
        
        logger.debug(
            "auth.validation.registration_validated",
            email=email.strip().lower(),
            has_full_name=full_name is not None
        )
    
    def validate_password_reset_data(self, email: str, reset_token: str, new_password: str) -> None:
        """
        Validate password reset data.
        
        Args:
            email: Email address
            reset_token: Password reset token
            new_password: New password
            
        Raises:
            ValidationError: If password reset data is invalid
        """
        self._validate_email_format(email)
        self.validate_token_format(reset_token)
        self._validate_password_strength(new_password)
        
        logger.debug(
            "auth.validation.password_reset_validated",
            email=email.strip().lower()
        )
    
    def _validate_email_format(self, email: str) -> None:
        """Validate email format."""
        if not self.email_pattern.match(email):
            raise ValidationError("Invalid email address format")
        
        if len(email) > 254:  # RFC 5321 limit
            raise ValidationError("Email address is too long")
    
    def _validate_password_format(self, password: str) -> None:
        """Validate basic password format for login."""
        if len(password) < self.min_password_length:
            raise ValidationError(
                f"Password must be at least {self.min_password_length} characters"
            )
        
        if len(password) > self.max_password_length:
            raise ValidationError(
                f"Password cannot exceed {self.max_password_length} characters"
            )
    
    def _validate_password_strength(self, password: str) -> None:
        """Validate password strength for registration/reset."""
        if not password:
            raise ValidationError("Password is required")
        
        # Length validation
        if len(password) < self.min_password_length:
            raise ValidationError(
                f"Password must be at least {self.min_password_length} characters long"
            )
        
        if len(password) > self.max_password_length:
            raise ValidationError(
                f"Password cannot exceed {self.max_password_length} characters"
            )
        
        # Strength requirements
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        if not (has_upper and has_lower and has_digit):
            raise ValidationError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit"
            )
        
        # Check for common weak passwords
        weak_passwords = {
            "password", "12345678", "qwerty123", "admin123", 
            "letmein", "welcome123", "password123"
        }
        
        if password.lower() in weak_passwords:
            raise ValidationError("Password is too common and not secure")
    
    def _validate_full_name(self, full_name: str) -> None:
        """Validate full name format."""
        if not full_name.strip():
            raise ValidationError("Full name cannot be empty")
        
        if len(full_name.strip()) < 2:
            raise ValidationError("Full name must be at least 2 characters")
        
        if len(full_name.strip()) > 100:
            raise ValidationError("Full name cannot exceed 100 characters")
        
        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-'\.]+$", full_name.strip()):
            raise ValidationError(
                "Full name can only contain letters, spaces, hyphens, and apostrophes"
            )
    
    def _is_valid_base64url(self, s: str) -> bool:
        """Check if string is valid base64url encoding."""
        try:
            # Base64url character set
            valid_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
            return all(c in valid_chars for c in s)
        except Exception:
            return False