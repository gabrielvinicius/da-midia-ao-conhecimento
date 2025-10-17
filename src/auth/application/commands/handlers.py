"""
Auth Command Handlers - Pure execution logic following Command Pattern
"""
import structlog
from typing import Dict, Any

from src.auth.config.settings import AuthSettings
from src.auth.domain.user import User
from src.auth.infrastructure.user_repository import UserRepository
from src.auth.utils.token import create_access_token
from src.auth.application.services.user_validator import UserValidator
from src.auth.application.services.password_service import PasswordService
from src.auth.application.services.user_factory import UserFactory
from src.shared.utils.password_utils import verify_password, hash_password
from .commands import (
    AuthenticateUserCommand,
    CreateUserCommand,
    ChangePasswordCommand,
    DeleteUserCommand,
    UpdateUserCommand
)

logger = structlog.get_logger(__name__)


class AuthenticateUserCommandHandler:
    """Handler for authenticate user command"""
    
    def __init__(self, user_repository: UserRepository, settings: AuthSettings):
        self.user_repository = user_repository
        self.settings = settings

    async def handle(self, command: AuthenticateUserCommand) -> Dict[str, Any]:
        """Execute user authentication command"""
        user = await self.user_repository.find_by_email(command.email)
        if not user or not verify_password(command.password, user.password_hash):
            return {
                "success": False,
                "token": None,
                "user": None,
                "message": "Invalid credentials"
            }
        
        token = create_access_token(user.id)
        logger.info("user.authenticated", user_id=str(user.id), email=command.email)
        
        return {
            "success": True,
            "token": token,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role
            },
            "message": "Authentication successful"
        }


class CreateUserCommandHandler:
    """Handler for create user command"""
    
    def __init__(
        self,
        user_repository: UserRepository,
        user_validator: UserValidator,
        password_service: PasswordService,
        user_factory: UserFactory,
    ):
        self.user_repository = user_repository
        self.user_validator = user_validator
        self.password_service = password_service
        self.user_factory = user_factory

    async def handle(self, command: CreateUserCommand) -> Dict[str, Any]:
        """Execute user creation command"""
        await self.user_validator.validate_new_user(command.email)
        hashed_password = self.password_service.hash_password(command.password)
        user = self.user_factory.create(command.email, hashed_password)
        created_user = await self.user_repository.save(user)
        
        logger.info("user.created", user_id=str(created_user.id), email=command.email)
        
        return {
            "success": True,
            "user": {
                "id": str(created_user.id),
                "email": created_user.email,
                "role": created_user.role
            },
            "message": "User created successfully"
        }


class ChangePasswordCommandHandler:
    """Handler for change password command"""
    
    def __init__(
        self,
        user_repository: UserRepository,
        password_service: PasswordService,
    ):
        self.user_repository = user_repository
        self.password_service = password_service

    async def handle(self, command: ChangePasswordCommand) -> Dict[str, Any]:
        """Execute password change command"""
        user = await self.user_repository.get_by_id(command.user_id)
        if not user:
            return {"success": False, "message": "User not found"}

        if not verify_password(command.old_password, user.password_hash):
            return {"success": False, "message": "Invalid old password"}

        new_password_hash = self.password_service.hash_password(command.new_password)
        updated_user = await self.user_repository.update_password(
            command.user_id, 
            new_password_hash
        )
        
        logger.info("user.password_changed", user_id=str(command.user_id))
        
        return {
            "success": True,
            "message": "Password changed successfully"
        }


class DeleteUserCommandHandler:
    """Handler for delete user command"""
    
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def handle(self, command: DeleteUserCommand) -> Dict[str, Any]:
        """Execute user deletion command"""
        user = await self.user_repository.get_by_id(command.user_id)
        if not user:
            return {"success": False, "message": "User not found"}

        success = await self.user_repository.delete(command.user_id)
        if not success:
            return {"success": False, "message": "Failed to delete user"}
            
        logger.info("user.deleted", 
                   user_id=str(command.user_id),
                   admin_user_id=str(command.admin_user_id))
        
        return {
            "success": True,
            "message": "User deleted successfully"
        }


class UpdateUserCommandHandler:
    """Handler for update user command"""
    
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def handle(self, command: UpdateUserCommand) -> Dict[str, Any]:
        """Execute user update command"""
        user = await self.user_repository.get_by_id(command.user_id)
        if not user:
            return {"success": False, "message": "User not found"}

        updated_user = await self.user_repository.update(
            command.user_id, 
            command.updates
        )
        
        logger.info("user.updated", 
                   user_id=str(command.user_id),
                   updates=command.updates,
                   admin_user_id=str(command.admin_user_id) if command.admin_user_id else None)
        
        return {
            "success": True,
            "user": {
                "id": str(updated_user.id),
                "email": updated_user.email,
                "role": updated_user.role
            },
            "message": "User updated successfully"
        }