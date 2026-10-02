"""O que o usuário é avisado em cada evento do processamento.

Antes, os textos e dados de cada aviso ficavam na montagem dos workers de
outros módulos (processamento e análise), que chamavam o serviço de avisos
diretamente. Agora o módulo de avisos reage aos eventos publicados, e os
demais nem sabem que ele existe.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from src.shared.domain.events import (
    AnalysisCompleted,
    AnalysisFailed,
    DomainEvent,
    MediaFailed,
    MediaProcessingFailed,
    TranscriptionCompleted,
    TranscriptionFailed,
)

FILE_FAILURE = "Falha durante o processamento do arquivo."


@dataclass(frozen=True)
class Notice:
    user_id: str
    message: str
    variables: Dict[str, Any] = field(default_factory=dict)


def completion_message(failed_steps: list[str]) -> str:
    """Texto do aviso de conclusão, citando as etapas que falharam, se houver."""
    if failed_steps:
        return (
            "Análise concluída com etapas incompletas ("
            + ", ".join(failed_steps)
            + "). Os resultados das demais etapas estão disponíveis."
        )
    return "Análise concluída. O resumo já está disponível."


def notice_for(event: DomainEvent) -> Optional[Notice]:
    """Aviso ao dono da mídia, ou None se o evento não pede aviso."""
    user_id = getattr(event, "user_id", None)
    if not user_id:
        return None
    base = {"media_id": str(event.media_id) if event.media_id else None, "evento": type(event).__name__}

    if isinstance(event, TranscriptionCompleted):
        return Notice(user_id, "Transcrição concluída com sucesso.", {**base, "transcription_id": event.transcription_id})
    if isinstance(event, TranscriptionFailed):
        return Notice(
            user_id, "Falha ao processar a transcrição.",
            {**base, "transcription_id": event.transcription_id, "erro": event.error_message},
        )
    if isinstance(event, (MediaProcessingFailed, MediaFailed)):
        return Notice(user_id, FILE_FAILURE, {**base, "stage": event.stage, "erro": event.error_message})
    if isinstance(event, AnalysisCompleted):
        return Notice(
            user_id, completion_message(event.failed_steps),
            {**base, "analysis_id": event.analysis_id, "transcription_id": event.transcription_id},
        )
    if isinstance(event, AnalysisFailed):
        return Notice(user_id, "Falha ao analisar o texto.", {**base, "erro": event.error_message})
    return None


NOTIFIED_EVENTS = (
    TranscriptionCompleted,
    TranscriptionFailed,
    MediaProcessingFailed,
    MediaFailed,
    AnalysisCompleted,
    AnalysisFailed,
)

__all__ = ["Notice", "notice_for", "completion_message", "NOTIFIED_EVENTS"]
