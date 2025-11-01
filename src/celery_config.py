"""Compatibility module exposing the project Celery application."""
from __future__ import annotations

from src.celery_app import celery as app

__all__ = ["app"]
