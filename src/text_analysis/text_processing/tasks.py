"""Compatibility Celery task entry point for text processing."""

from __future__ import annotations

from src.text_analysis.tasks import analyze_task

__all__ = ["analyze_task"]

