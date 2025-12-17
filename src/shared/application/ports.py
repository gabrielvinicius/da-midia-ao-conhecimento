from __future__ import annotations

from typing import Any, Protocol


class ModuleRegistryPort(Protocol):
    """Expose domain service registry for diagnostics or cross-cutting access."""

    def attach(self, app: Any) -> None: ...
    def get(self) -> Any: ...


__all__ = ["ModuleRegistryPort"]
