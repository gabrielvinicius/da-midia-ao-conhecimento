"""Pedido de análise pela fila: a API nunca executa os modelos."""
from __future__ import annotations

from src.shared.events.integration_events import QUEUE_TEXT_ANALYSIS, TASK_TEXT_ANALYSIS_ANALYZE
from src.shared.infrastructure.tasks.sender import send_task
from src.text_analysis.application.ports import AnalysisQueuePort


class CeleryAnalysisQueue(AnalysisQueuePort):
    def request_analysis(self, payload: dict) -> None:
        send_task(TASK_TEXT_ANALYSIS_ANALYZE, payload, QUEUE_TEXT_ANALYSIS)


__all__ = ["CeleryAnalysisQueue"]
