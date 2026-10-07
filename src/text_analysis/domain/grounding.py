"""Verificação de fidelidade do resumo: cada frase tem apoio na transcrição?

Para cada frase do resumo, procura o trecho da transcrição mais parecido (por
similaridade entre vetores) e considera a frase apoiada se a similaridade
passa de um limiar. É uma heurística, não uma prova: detecta frases sobre
assuntos que não aparecem na gravação (o tipo de invenção mais comum dos
modelos de linguagem), mas não percebe um nome trocado dentro de uma frase
sobre o assunto certo. Por isso complementa, e não substitui, a avaliação
humana da fidelidade.

Duas verificações completam a primeira, porque um resumo com todas as frases
apoiadas ainda pode ser ruim (caso visto na avaliação: 57 de 57 frases
apoiadas num resumo sem a conclusão e sem um trecho do meio):

- Cobertura: a gravação é dividida em janelas de tempo, e cada frase apoiada
  marca a janela do seu trecho mais parecido. Janelas sem nenhuma frase são
  partes da gravação que o resumo não menciona.
- Números: cada número de uma frase precisa aparecer em algum dos trechos mais
  parecidos com ela. Pega um número que não está naquele assunto, mas não um
  número deslocado para outro fato do mesmo trecho.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, Sequence

import numpy as np

MIN_WORDS = 6  # frases menores (títulos, rótulos) não são verificadas

# Cobertura: uma janela a cada SENTENCES_PER_WINDOW frases do resumo, entre o
# mínimo e o máximo (um resumo curto não cobre uma aula minuto a minuto).
SENTENCES_PER_WINDOW = 4
MIN_WINDOWS = 4
MAX_WINDOWS = 12
# Números: trechos mais parecidos com a frase em que o número deve aparecer.
NUMBER_PASSAGES = 3

_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
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
class CoverageGap:
    """Parte da gravação (s) sem nenhuma frase do resumo."""

    start: float
    end: float


@dataclass(frozen=True)
class NumberIssue:
    """Frase com número(s) que não aparecem nos trechos do mesmo assunto."""

    text: str
    numbers: list[str]


@dataclass(frozen=True)
class GroundingReport:
    checked: int
    supported: int
    threshold: float
    unsupported: list[UnsupportedSentence] = field(default_factory=list)
    windows: int = 0  # janelas de tempo da cobertura (0: documento, sem horários)
    gaps: list[CoverageGap] = field(default_factory=list)
    number_issues: list[NumberIssue] = field(default_factory=list)

    @property
    def ratio(self) -> Optional[float]:
        return self.supported / self.checked if self.checked else None

    @property
    def coverage(self) -> Optional[float]:
        return (self.windows - len(self.gaps)) / self.windows if self.windows else None

    @classmethod
    def from_dict(cls, data: dict) -> "GroundingReport":
        return cls(
            checked=int(data.get("checked") or 0),
            supported=int(data.get("supported") or 0),
            threshold=float(data.get("threshold") or 0.0),
            unsupported=[
                UnsupportedSentence(
                    text=str(u.get("text", "")),
                    best_score=float(u.get("best_score") or 0.0),
                    closest_start=u.get("closest_start"),
                )
                for u in data.get("unsupported") or []
            ],
            windows=int(data.get("windows") or 0),
            gaps=[CoverageGap(float(g["start"]), float(g["end"])) for g in data.get("gaps") or []],
            number_issues=[
                NumberIssue(text=str(n.get("text", "")), numbers=[str(x) for x in n.get("numbers") or []])
                for n in data.get("number_issues") or []
            ],
        )

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
            "windows": self.windows,
            "coverage": round(self.coverage, 3) if self.coverage is not None else None,
            "gaps": [{"start": round(g.start, 1), "end": round(g.end, 1)} for g in self.gaps],
            "number_issues": [{"text": n.text, "numbers": n.numbers} for n in self.number_issues],
        }


def assess_grounding(
    sentences: Sequence[str],
    sentence_vectors: Sequence[Sequence[float]],
    passage_vectors: Sequence[Sequence[float]],
    passage_starts: Sequence[Optional[float]],
    threshold: float,
    passage_texts: Optional[Sequence[str]] = None,
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
    supported = best >= threshold
    unsupported = [
        UnsupportedSentence(
            text=sentences[i],
            best_score=float(best[i]),
            closest_start=passage_starts[int(best_idx[i])] if passage_starts else None,
        )
        for i in range(len(sentences))
        if not supported[i]
    ]
    windows, gaps = coverage_gaps(
        [int(best_idx[i]) for i in range(len(sentences)) if supported[i]], passage_starts, len(sentences)
    )
    return GroundingReport(
        checked=len(sentences),
        supported=len(sentences) - len(unsupported),
        threshold=threshold,
        unsupported=unsupported,
        windows=windows,
        gaps=gaps,
        number_issues=number_issues(sentences, similarity, passage_texts) if passage_texts else [],
    )


def coverage_gaps(
    supported_passages: Sequence[int], passage_starts: Sequence[Optional[float]], sentence_count: int
) -> tuple[int, list[CoverageGap]]:
    """Janelas de tempo sem nenhuma frase apoiada (trecho mais parecido nela).

    Documentos (trechos sem horário) não têm linha do tempo: (0, []).
    """
    times = [t for t in passage_starts if t is not None]
    if not times or max(times) <= 0:
        return 0, []
    windows = max(MIN_WINDOWS, min(MAX_WINDOWS, sentence_count // SENTENCES_PER_WINDOW))
    width = max(times) / windows
    covered = {
        min(int(passage_starts[i] // width), windows - 1)
        for i in supported_passages
        if passage_starts[i] is not None
    }
    return windows, [
        CoverageGap(start=w * width, end=(w + 1) * width) for w in range(windows) if w not in covered
    ]


def number_issues(
    sentences: Sequence[str], similarity: np.ndarray, passage_texts: Sequence[str]
) -> list[NumberIssue]:
    """Frases com números ausentes dos trechos mais parecidos com elas."""
    issues = []
    order = np.argsort(-similarity, axis=1)
    for i, sentence in enumerate(sentences):
        numbers = _numbers(sentence)
        if not numbers:
            continue
        # Uma frase do resumo que junta vários fatos precisa de mais trechos.
        nearby: set[str] = set()
        for j in order[i][: NUMBER_PASSAGES + len(numbers)]:
            nearby |= _numbers(passage_texts[int(j)])
        missing = sorted((n for n in numbers if not _found(n, nearby)), key=sentence.find)
        if missing:
            issues.append(NumberIssue(text=sentence, numbers=missing))
    return issues


def _numbers(text: str) -> set[str]:
    """Números do texto sem separadores (1.000 e 1000 são o mesmo)."""
    return {re.sub(r"[.,]", "", n) for n in _NUMBER.findall(text or "")}


def _found(number: str, nearby: set[str]) -> bool:
    """O resumo escreve "década de 1960" quando a fala diz "década de 60"."""
    if number in nearby:
        return True
    return len(number) == 4 and number.startswith("19") and number.endswith("0") and number[2:] in nearby


def _normalized(vectors: Sequence[Sequence[float]]) -> np.ndarray:
    m = np.asarray(vectors, dtype="float32")
    norms = np.linalg.norm(m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return m / norms
