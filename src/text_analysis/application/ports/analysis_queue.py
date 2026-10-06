from __future__ import annotations

from typing import Protocol


class AnalysisQueuePort(Protocol):
    """Pede a análise ao worker (fila). A API não roda os modelos."""

    def request_analysis(self, payload: dict) -> None: ...
