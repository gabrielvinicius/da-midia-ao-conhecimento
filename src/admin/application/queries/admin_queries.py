"""Backward compatibility wrapper for AdminQueries."""

from .admin_read_service import AdminReadService as AdminQueries

__all__ = ["AdminQueries"]
