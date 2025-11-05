"""Backward-compatible module exposing ProcessVideoCommandHandler."""

from .handlers import ProcessVideoCommandHandler
from .handlers import av as _av

# Preserve historical attribute access for tests/legacy imports.
av = _av

# Keep handlers.av and this module in sync for monkeypatch compatibility.
from . import handlers as _handlers

_handlers.av = av

__all__ = ["ProcessVideoCommandHandler", "av"]
