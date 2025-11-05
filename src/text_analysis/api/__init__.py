"""Unified API entrypoint for text analysis."""

from . import routers

router = routers.router

__all__ = ["router"]
