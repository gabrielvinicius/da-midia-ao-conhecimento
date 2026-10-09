"""Revisão espaçada das perguntas de estudo (caixas de Leitner).

Cada pergunta está numa caixa de 1 a 5. Acertar sobe uma caixa e afasta a
próxima revisão (hoje, 1, 3, 7 e 14 dias); errar volta para a caixa 1, para
rever ainda hoje. A partir da caixa 4 a pergunta conta como dominada.
"""
from __future__ import annotations

import datetime
import hashlib
import re
import unicodedata
from dataclasses import dataclass, replace
from typing import Optional

INTERVAL_DAYS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 14}
MASTERED_BOX = 4


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
class ReviewCard:
    box: int = 1
    correct_count: int = 0
    wrong_count: int = 0
    last_answered_at: Optional[datetime.datetime] = None
    due_at: Optional[datetime.datetime] = None  # None: nunca respondida

    def answered(self, correct: bool, now: datetime.datetime) -> "ReviewCard":
        box = min(self.box + 1, max(INTERVAL_DAYS)) if correct else 1
        return replace(
            self,
            box=box,
            correct_count=self.correct_count + (1 if correct else 0),
            wrong_count=self.wrong_count + (0 if correct else 1),
            last_answered_at=now,
            due_at=now + datetime.timedelta(days=INTERVAL_DAYS[box]),
        )

    def is_due(self, now: datetime.datetime) -> bool:
        return self.due_at is None or self.due_at <= now

    @property
    def mastered(self) -> bool:
        return self.box >= MASTERED_BOX


__all__ = ["INTERVAL_DAYS", "MASTERED_BOX", "ReviewCard", "normalized", "question_key"]
