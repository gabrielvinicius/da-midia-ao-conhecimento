"""Momento de uma gravação no formato lido pelo usuário (mm:ss ou h:mm:ss).

Usado na descrição dos quadros (processamento) e no resumo (análise); antes,
cada módulo tinha a sua cópia.
"""
from __future__ import annotations

from typing import Optional


def format_timestamp(seconds: Optional[float]) -> Optional[str]:
    if seconds is None:
        return None
    total = int(max(0, seconds))
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes:02d}:{secs:02d}"


__all__ = ["format_timestamp"]
