"""
Password Service - Single Responsibility: Password Management
"""
from uuid import UUID
from src.auth.application.commands.change_password_command import ChangePasswordCommand
from src.auth.application.commands.change_password_command_handler import ChangePasswordCommandHandler
from src.shared.utils.password_utils import verify_password, hash_password


class PasswordService:
    """
    Service responsible ONLY for password management operations.
    
    Single Responsibility: Handle password-related operations (change, validate, etc).
    """
    
    def __init__(self, change_password_handler: ChangePasswordCommandHandler):
        self.change_password_handler = change_password_handler
    
    async def change_password(self, user_id: UUID, old_password: str, new_password: str) -> None:
        """
        Change user's password.
        
        Args:
            user_id: ID of user changing password
            old_password: Current password for verification
            new_password: New password to set
            
        Raises:
            ValueError: If old password is incorrect or new password is invalid
        """
        # Validate new password before sending command
        self.validate_password_strength(new_password)
        
        command = ChangePasswordCommand(
            user_id=user_id,
            old_password=old_password,
            new_password=new_password
        )
        await self.change_password_handler.handle(command)
    
    def validate_password_strength(self, password: str) -> None:
        """
        Validate password meets security requirements.
        
        Args:
            password: Password to validate
            
        Raises:
            ValueError: If password doesn't meet requirements
        """
        if not password:
            raise ValueError("Password cannot be empty")
        
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        # Check for at least one uppercase letter
        if not any(c.isupper() for c in password):
            raise ValueError("Password must contain at least one uppercase letter")
        
        # Check for at least one lowercase letter
        if not any(c.islower() for c in password):
            raise ValueError("Password must contain at least one lowercase letter")
        
        # Check for at least one digit
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain at least one number")
        
        # Check for special characters
        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(c in special_chars for c in password):
            raise ValueError("Password must contain at least one special character")
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            plain_password: Plain text password
            hashed_password: Hashed password to compare against
            
        Returns:
            bool: True if password matches, False otherwise
        """
        return verify_password(plain_password, hashed_password)
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password for storage.
        
        Args:
            password: Plain text password to hash
            
        Returns:
            str: Hashed password
        """
        return hash_password(password)
    
    async def generate_password_reset_token(self, user_id: UUID) -> str:
        """
        Generate a password reset token for a user.
        
        Args:
            user_id: ID of user requesting password reset
            
        Returns:
            str: Password reset token
        """
        # Implementation for password reset token generation
        # This would typically involve creating a time-limited token
        pass
    
    async def validate_password_reset_token(self, token: str) -> UUID:
        """
        Validate a password reset token and return user ID.
        
        Args:
            token: Password reset token to validate
            
        Returns:
            UUID: User ID if token is valid
            
        Raises:
            ValueError: If token is invalid or expired
        """
        # Implementation for password reset token validation
        pass
    
    async def reset_password_with_token(self, token: str, new_password: str) -> None:
        """
        Reset password using a valid reset token.
        
        Args:
            token: Valid password reset token
            new_password: New password to set
            
        Raises:
            ValueError: If token is invalid or password is weak
        """
        # Validate new password
        self.validate_password_strength(new_password)
        
        # Validate token and get user ID
        user_id = await self.validate_password_reset_token(token)
        
        # Implementation for resetting password with token
        pass