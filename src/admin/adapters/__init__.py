"""Adapters that allow the admin facade to interact with legacy modules."""

from .user_management_adapter import UserManagementAdapter
from .media_management_adapter import MediaManagementAdapter

__all__ = [
    "MediaManagementAdapter",
    "UserManagementAdapter",
]
