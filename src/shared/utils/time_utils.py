"""Shared helpers for timezone-aware timestamps."""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """Return the current UTC time as an aware datetime."""
    return datetime.now(timezone.utc)
