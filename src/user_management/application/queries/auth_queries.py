"""Backward compatibility wrapper importing AuthQueries from user_management."""

from src.user_management.application.auth_queries import AuthQueries

__all__ = ["AuthQueries"]
