"""Verificação de fidelidade do resumo: cada frase tem apoio na transcrição?

Para cada frase do resumo, procura o trecho da transcrição mais parecido (por
similaridade entre vetores) e considera a frase apoiada se a similaridade
passa de um limiar. É uma heurística, não uma prova: detecta frases sobre
assuntos que não aparecem na gravação (o tipo de invenção mais comum dos
modelos de linguagem), mas não percebe um número ou um nome trocado dentro de
uma frase sobre o assunto certo. Por isso complementa, e não substitui, a
avaliação humana da fidelidade.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np

MIN_WORDS = 6  # frases menores (títulos, rótulos) não são verificadas

_HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
_MARKUP = re.compile(r"[*_`>|]+")
_LIST_MARK = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-ZÀ-Ú0-9\"“(])")


def split_sentences(markdown: str) -> list[str]:
    """Frases verificáveis de um texto em Markdown (sem títulos nem marcação)."""
    sentences: list[str] = []
    for line in (markdown or "").splitlines():
        if not line.strip() or _HEADING.match(line) or line.strip() == "---":
            continue
        line = _MARKUP.sub("", _LIST_MARK.sub("", line)).strip()
        for sentence in _SENTENCE_END.split(line):
            sentence = sentence.strip()
            if len(sentence.split()) >= MIN_WORDS:
                sentences.append(sentence)
    return sentences


@dataclass(frozen=True)
class UnsupportedSentence:
    text: str
    best_score: float
    closest_start: Optional[float] = None  # momento do trecho mais próximo (s)


@dataclass(frozen=True)
class GroundingReport:
    checked: int
    supported: int
    threshold: float
    unsupported: list[UnsupportedSentence] = field(default_factory=list)

    @property
    def ratio(self) -> Optional[float]:
        return self.supported / self.checked if self.checked else None

    def to_dict(self) -> dict:
        return {
            "checked": self.checked,
            "supported": self.supported,
            "ratio": round(self.ratio, 3) if self.ratio is not None else None,
            "threshold": self.threshold,
            "unsupported": [
                {
                    "text": u.text,
                    "best_score": round(u.best_score, 3),
                    "closest_start": u.closest_start,
                }
                for u in self.unsupported
            ],
        }


def assess_grounding(
    sentences: Sequence[str],
    sentence_vectors: Sequence[Sequence[float]],
    passage_vectors: Sequence[Sequence[float]],
    passage_starts: Sequence[Optional[float]],
    threshold: float,
) -> GroundingReport:
    """Compara cada frase com todos os trechos (vetores normalizados: o produto
    escalar é a similaridade do cosseno)."""
    if not sentences or not len(passage_vectors):
        return GroundingReport(checked=0, supported=0, threshold=threshold)
    s = _normalized(sentence_vectors)
    p = _normalized(passage_vectors)
    similarity = s @ p.T  # frases × trechos
    best_idx = similarity.argmax(axis=1)
    best = similarity[np.arange(len(sentences)), best_idx]
    unsupported = [
        UnsupportedSentence(
            text=sentences[i],
            best_score=float(best[i]),
            closest_start=passage_starts[int(best_idx[i])] if passage_starts else None,
        )
        for i in range(len(sentences))
        if best[i] < threshold
    ]
    return GroundingReport(
        checked=len(sentences),
        supported=len(sentences) - len(unsupported),
        threshold=threshold,
        unsupported=unsupported,
    )


def _normalized(vectors: Sequence[Sequence[float]]) -> np.ndarray:
    m = np.asarray(vectors, dtype="float32")
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return m / norms
