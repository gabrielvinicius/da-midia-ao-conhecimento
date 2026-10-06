"""LLM text generation port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional


class TextGenerationUnavailableError(RuntimeError):
    """Nenhum modelo (nem o principal nem o reserva) gerou o texto.

    Os adaptadores lançam este erro em vez de devolver um texto substituto:
    quem chama decide o que fazer (a síntese monta o resumo simplificado, os
    títulos mantêm os do BERTopic). Um texto substituto parecia um resumo
    real e era rotulado como se tivesse vindo de um modelo.
    """


class TextGenerationPort(ABC):
    #: True quando a última resposta veio do modelo reserva, e não do principal.
    last_used_reserve: bool = False
    #: Tokens do último prompt, quando o adaptador sabe contar (None se não).
    last_prompt_tokens: Optional[int] = None
    #: True se o último prompt pode ter sido cortado por exceder a janela.
    last_prompt_truncated: bool = False

    @abstractmethod
    async def summarize_topic(
        self,
        title_hint: Optional[str],
        content: str,
        keywords: list[str],
        language: str,
        *,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Gera texto em Markdown; ``max_tokens`` limita o tamanho da resposta.

        Raises:
            TextGenerationUnavailableError: se nenhum modelo respondeu.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the model is available for use."""

    async def release(self) -> None:
        """Libera a memória (GPU) ocupada pelo modelo, se o adaptador puder.

        Chamado ao fim de cada análise: a GPU de 12 GB é compartilhada com a
        transcrição e o modelo de visão, e um modelo ocioso não deve ocupá-la.
        """
