from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)

__all__ = ["utcnow"]
