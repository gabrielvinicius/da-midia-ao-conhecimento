"""
Authentication Service - Single Responsibility: User Authentication
"""
from typing import Optional
from src.auth.application.commands.authenticate_user_command import AuthenticateUserCommand
from src.auth.application.commands.authenticate_user_command_handler import AuthenticateUserCommandHandler


class AuthenticationService:
    """
    Service responsible ONLY for user authentication operations.
    
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