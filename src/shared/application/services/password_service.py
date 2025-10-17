# src/shared/application/services/password_service.py
"""
Password Service implementation following SRP principle.
Responsible only for password operations.
"""
import secrets
import string
import structlog
from typing import Optional

from src.shared.domain.interfaces import PasswordService as IPasswordService
from src.shared.utils.password_utils import hash_password, verify_password

logger = structlog.get_logger(__name__)


class PasswordService(IPasswordService):
    """
    Password operations service implementation.
    Follows SRP: Only responsible for password hashing, verification, and generation.
    """
    
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        if not password:
            raise ValueError("Password cannot be empty")
        
        logger.debug("password.hash.started")
        
        try:
            hashed = hash_password(password)
            logger.debug("password.hash.completed")
            return hashed
            
        except Exception as e:
            logger.error("password.hash.failed", error=str(e))
            raise
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        if not password or not hashed:
            return False
        
        logger.debug("password.verify.started")
        
        try:
            is_valid = verify_password(password, hashed)
            logger.debug("password.verify.completed", is_valid=is_valid)
            return is_valid
            
        except Exception as e:
            logger.error("password.verify.failed", error=str(e))
            return False
    
    def generate_password(self, length: int = 12) -> str:
        """Generate a secure random password."""
        if length < 4:
            raise ValueError("Password length must be at least 4")
        
        logger.debug("password.generate.started", length=length)
        
        # Ensure password contains at least one character from each category
        lowercase = string.ascii_lowercase
        uppercase = string.ascii_uppercase
        digits = string.digits
        symbols = "!@#$%^&*"
        
        # Start with at least one from each category
        password = [
            secrets.choice(lowercase),
            secrets.choice(uppercase),
            secrets.choice(digits),
            secrets.choice(symbols)
        ]
        
        # Fill the rest randomly
        all_chars = lowercase + uppercase + digits + symbols
        for _ in range(length - 4):
            password.append(secrets.choice(all_chars))
        
        # Shuffle the password list
        secrets.SystemRandom().shuffle(password)
        
        generated_password = ''.join(password)
        logger.debug("password.generate.completed", length=len(generated_password))
        
        return generated_password
    
    def validate_password_strength(self, password: str) -> dict:
        """Validate password strength and return feedback."""
        if not password:
            return {"valid": False, "errors": ["Password cannot be empty"]}
        
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if not any(c.islower() for c in password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not any(c.isupper() for c in password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not any(c.isdigit() for c in password):
            errors.append("Password must contain at least one digit")
        
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            errors.append("Password must contain at least one special character")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "strength": self._calculate_strength(password)
        }
    
    def _calculate_strength(self, password: str) -> str:
        """Calculate password strength."""
        score = 0
        
        if len(password) >= 8:
            score += 1
        if len(password) >= 12:
            score += 1
        if any(c.islower() for c in password):
            score += 1
        if any(c.isupper() for c in password):
            score += 1
        if any(c.isdigit() for c in password):
            score += 1
        if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            score += 1
        
        if score >= 5:
            return "strong"
        elif score >= 3:
            return "medium"
        else:
            return "weak"