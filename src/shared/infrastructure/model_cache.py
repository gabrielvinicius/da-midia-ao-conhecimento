"""Cache dos modelos de IA carregados no processo.

Carregar um modelo leva segundos e ocupa memória da GPU; criar um adaptador
novo a cada análise deixava cópias na placa até o coletor de lixo agir. Por
isso cada processo guarda uma instância por modelo. É a exceção, documentada
no AGENTS.md, à regra de não usar estado global: fica concentrada aqui, com
chave explícita, e não espalhada em variáveis soltas de cada módulo.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Hashable, TypeVar

T = TypeVar("T")


class ModelCache:
    def __init__(self) -> None:
        self._instances: Dict[Hashable, Any] = {}

    def get_or_create(self, key: Hashable, factory: Callable[[], T]) -> T:
        if key not in self._instances:
            self._instances[key] = factory()
        return self._instances[key]

    def peek(self, key: Hashable) -> Any:
        """A instância já carregada, sem criar uma nova (None se não houver)."""
        return self._instances.get(key)

    def clear(self) -> None:
        """Esquece as instâncias (testes e reinício do processo)."""
        self._instances.clear()


# Uma por processo (API ou worker).
model_cache = ModelCache()

__all__ = ["ModelCache", "model_cache"]
