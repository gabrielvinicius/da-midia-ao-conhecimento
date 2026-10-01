"""Recursos que o pipeline libera para dividir uma única GPU entre modelos."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ReleasablePort(Protocol):
    """Algo que ocupa memória (em geral, da GPU) e pode devolvê-la.

    A GPU de referência tem 12 GB e é compartilhada pelo modelo de
    transcrição, pelos modelos do worker (sentimento, vetores, visão) e pelo
    modelo de linguagem no Ollama. Liberar cada modelo quando deixa de ser
    usado evita que o Ollama fique sem memória e passe a rodar na CPU.
    """

    async def release(self) -> None:
        ...
