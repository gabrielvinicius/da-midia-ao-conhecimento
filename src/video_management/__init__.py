"""Compatibility package exposing legacy video management API."""

from .application.commands import UploadVideoCommand, UploadVideoCommandHandler
from .domain.video import Video

__all__ = ["UploadVideoCommand", "UploadVideoCommandHandler", "Video"]
