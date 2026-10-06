"""Envio de tarefas pelo nome, sem importar o módulo que as executa.

O nome de cada tarefa e a fila são um contrato compartilhado
(src.shared.events.integration_events).
"""
from __future__ import annotations

from typing import Any

# Uma queda curta do Redis não deve perder a tarefa: o envio tenta de novo
# por alguns segundos antes de desistir (e o chamador tratar a falha).
SEND_RETRY_POLICY = {"max_retries": 4, "interval_start": 1, "interval_step": 2, "interval_max": 5}


def send_task(task_name: str, kwargs: dict, queue: str) -> Any:
    from src.celery_app import celery

    return celery.send_task(
        task_name, kwargs=kwargs, queue=queue, retry=True, retry_policy=SEND_RETRY_POLICY
    )


__all__ = ["SEND_RETRY_POLICY", "send_task"]
