"""Reranking port: reordena os candidatos da busca por relevância."""

from __future__ import annotations

from abc import ABC, abstractmethod


class RerankerPort(ABC):
    """Lê a pergunta junto com cada trecho candidato e dá uma nota de relevância.

    A busca por vetores compara pergunta e trecho separadamente e é rápida para
    varrer o acervo; o reranqueador lê os dois juntos e ordena melhor os
    poucos candidatos que ela trouxe.
    """

    @abstractmethod
    def score(self, query: str, passages: list[str]) -> list[float]:
        """Notas entre 0 e 1, na ordem dos trechos (maior = mais relevante)."""
