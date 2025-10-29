"""Backward compatibility wrapper importing AuthService from user_management."""

from src.user_management.application.auth_service import AuthService

__all__ = ["AuthService"]
