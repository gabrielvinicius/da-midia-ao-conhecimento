from __future__ import annotations

import time
import uuid
from typing import Any, Optional


async def record_operation(
    metrics: Any,
    operation: str,
    *,
    user_id: Optional[uuid.UUID],
    media_id: Any,
    success: bool,
    started: float,
) -> None:
    """Registra a duração e o resultado da operação (métricas são opcionais)."""
    if not metrics or not hasattr(metrics, "record_operation"):
        return
    await metrics.record_operation(
        operation=operation,
        user_id=str(user_id) if user_id else "unknown",
        status="success" if success else "failure",
        duration=time.monotonic() - started,
        media_id=str(media_id),
        media_type="unknown",
        provider=None,
    )
