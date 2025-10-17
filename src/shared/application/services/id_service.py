# src/shared/application/services/id_service.py
"""
ID Service implementation following SRP principle.
Responsible only for ID generation operations.
"""
import uuid
import secrets
import string
from uuid import UUID

from src.shared.domain.interfaces import IdService as IIdService


class IdService(IIdService):
    """
    ID generation service implementation.
    Follows SRP: Only responsible for generating various types of IDs.
    """
    
    def generate_uuid(self) -> UUID:
        """Generate a new UUID."""
        return uuid.uuid4()
    
    def generate_short_id(self, length: int = 8) -> str:
        """Generate a short alphanumeric ID."""
        if length < 1:
            raise ValueError("Length must be at least 1")
        
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def generate_secure_token(self, length: int = 32) -> str:
        """Generate a secure random token."""
        if length < 1:
            raise ValueError("Length must be at least 1")
        
        return secrets.token_urlsafe(length)
    
    def generate_numeric_id(self, length: int = 6) -> str:
        """Generate a numeric ID."""
        if length < 1:
            raise ValueError("Length must be at least 1")
        
        return ''.join(secrets.choice(string.digits) for _ in range(length))
    
    def generate_session_id(self) -> str:
        """Generate a session ID."""
        return self.generate_secure_token(24)
    
    def generate_api_key(self) -> str:
        """Generate an API key."""
        return f"sk_{self.generate_secure_token(40)}"