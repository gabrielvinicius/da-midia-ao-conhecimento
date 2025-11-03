"""Compatibility command objects for legacy video processing flow."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ProcessVideoCommand:
    media_id: str
    file_path: str


__all__ = ["ProcessVideoCommand"]
