"""Backwards compatible exports for the media aggregate."""

from src.shared.domain.enums import MediaStatus, MediaType
from src.media_management.domain.model import MediaAggregate

# Historical imports referenced Media as the SQLAlchemy entity. We now expose the
# pure domain aggregate under the same name to minimise churn in the codebase.
Media = MediaAggregate

__all__ = ["Media", "MediaAggregate", "MediaStatus", "MediaType"]
