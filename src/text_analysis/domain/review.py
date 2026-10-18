"""Revisão espaçada das perguntas de estudo (caixas de Leitner).

Cada pergunta está numa caixa. Acertar sobe uma caixa e afasta a próxima
revisão; errar volta para a caixa 1. Com o padrão (REVIEW_INTERVAL_DAYS e
REVIEW_MASTERED_BOX), são 5 caixas, com revisão hoje, em 1, 3, 7 e 14 dias, e
a pergunta conta como dominada a partir da caixa 4 (três acertos seguidos).
"""
from __future__ import annotations

import datetime
import hashlib
import re
import unicodedata
from dataclasses import dataclass, replace
from typing import Optional



def normalized(text: str) -> str:
    """Minúsculas, sem acentos nem pontuação: "Proteção de Dados!" e
    "proteção de dados" são o mesmo texto."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    plain = "".join(c for c in decomposed if not unicodedata.combining(c)).lower()
    return " ".join(re.sub(r"[^\w\s]", " ", plain).split())


def question_key(question: str) -> str:
    """Identifica a pergunta pelo texto: a lista pode mudar de ordem quando o
    usuário corrige as perguntas, e o progresso acompanha o texto."""
    return hashlib.sha256(normalized(question).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class ReviewSchedule:
    """Dias até a próxima revisão em cada caixa (o primeiro é o da caixa 1) e
    a caixa a partir da qual a pergunta conta como dominada."""

    interval_days: tuple[int, ...] = (0, 1, 3, 7, 14)
    mastered_box: int = 4

    def __post_init__(self) -> None:
        if not self.interval_days or any(d < 0 for d in self.interval_days):
            raise ValueError("REVIEW_INTERVAL_DAYS precisa de ao menos um número de dias, nenhum negativo")
        if not 1 <= self.mastered_box <= len(self.interval_days):
            raise ValueError("REVIEW_MASTERED_BOX precisa ser uma das caixas de REVIEW_INTERVAL_DAYS")

    @property
    def boxes(self) -> int:
        return len(self.interval_days)

    def days_until_review(self, box: int) -> int:
        return self.interval_days[min(max(box, 1), self.boxes) - 1]

    def is_mastered(self, card: "ReviewCard") -> bool:
        return card.box >= self.mastered_box


DEFAULT_SCHEDULE = ReviewSchedule()


@dataclass(frozen=True)
class ReviewCard:
    box: int = 1
    correct_count: int = 0
    wrong_count: int = 0
    last_answered_at: Optional[datetime.datetime] = None
    due_at: Optional[datetime.datetime] = None  # None: nunca respondida

    def answered(
        self, correct: bool, now: datetime.datetime, schedule: ReviewSchedule = DEFAULT_SCHEDULE
    ) -> "ReviewCard":
        box = min(self.box + 1, schedule.boxes) if correct else 1
        return replace(
            self,
            box=box,
            correct_count=self.correct_count + (1 if correct else 0),
            wrong_count=self.wrong_count + (0 if correct else 1),
            last_answered_at=now,
            due_at=now + datetime.timedelta(days=schedule.days_until_review(box)),
        )

    def is_due(self, now: datetime.datetime) -> bool:
        return self.due_at is None or self.due_at <= now


__all__ = ["DEFAULT_SCHEDULE", "ReviewCard", "ReviewSchedule", "normalized", "question_key"]
