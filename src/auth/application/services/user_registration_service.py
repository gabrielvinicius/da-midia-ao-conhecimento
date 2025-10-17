"""
User Registration Service - Single Responsibility: User Registration
"""
from src.auth.domain.user import User
from src.auth.application.commands.commands import CreateUserCommand
from src.auth.application.commands.handlers import CreateUserCommandHandler


class UserRegistrationService:
    """
    Service responsible ONLY for user registration operations.
    
    Single Responsibility: Handle new user registration flows.
    """
    
    def __init__(self, create_user_handler: CreateUserCommandHandler):
        self.create_user_handler = create_user_handler
    
    async def register_user(self, email: str, password: str) -> User:
        """
        Register a new user in the system.
        
        Args:
            email: User's email address
            password: User's password
            
        Returns:
            User: The created user object
            
        Raises:
            ValueError: If email already exists or validation fails
        """
        command = CreateUserCommand(email=email, password=password)
        return await self.create_user_handler.handle(command)
    
    async def validate_registration_data(self, email: str, password: str) -> None:
        """
        Validate registration data before creating user.
        
        Args:
            email: Email to validate
            password: Password to validate
            
        Raises:
            ValueError: If validation fails
        """
        # Email validation
        if not email or '@' not in email:
            raise ValueError("Invalid email address")
        
        # Password validation
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters")
        
        # Additional validation rules can be added here
    
    async def check_email_availability(self, email: str) -> bool:
        """
        Check if email is available for registration.
        
        Args:
            email: Email to check
            
        Returns:
            bool: True if email is available, False if already taken
        """
        # This would check against repository
        # Implementation depends on user repository
        pass