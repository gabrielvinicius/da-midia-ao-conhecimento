"""Adapters that allow the admin facade to interact with legacy modules."""

from .media_management_adapter import MediaManagementAdapter
from .user_management_adapter import UserManagementAdapter

__all__ = [
    "MediaManagementAdapter",
    "UserManagementAdapter",
]
