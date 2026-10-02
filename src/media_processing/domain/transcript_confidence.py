"""Confiança de uma transcrição, a partir da de cada segmento.

O Whisper dá, por segmento, a média do log da probabilidade dos tokens
(avg_logprob, gravado como "confidence"). exp() disso é a probabilidade média
por token, entre 0 e 1; a da transcrição é a média dos segmentos ponderada pela
duração. Antes, o campo ficava sempre em 0: nada o calculava.
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Optional


def transcript_confidence(segments: Iterable[dict[str, Any]]) -> Optional[float]:
    total = weighted = 0.0
    for segment in segments or []:
        logprob = segment.get("confidence")
        if not isinstance(logprob, (int, float)):
            continue
        start, end = segment.get("start"), segment.get("end")
        weight = end - start if isinstance(start, (int, float)) and isinstance(end, (int, float)) and end > start else 1.0
        weighted += min(1.0, math.exp(logprob)) * weight
        total += weight
    return round(weighted / total, 3) if total else None


__all__ = ["transcript_confidence"]
