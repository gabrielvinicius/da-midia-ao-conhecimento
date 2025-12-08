"""Backward compatibility wrapper for Admin Commands."""

from .dto import (
    DeleteMediaCommand,
    DeleteUserCommand,
    ReprocessMediaCommand,
    UpdateUserRoleCommand,
)

__all__ = [
    "DeleteMediaCommand",
    "DeleteUserCommand",
    "ReprocessMediaCommand",
    "UpdateUserRoleCommand",
]
