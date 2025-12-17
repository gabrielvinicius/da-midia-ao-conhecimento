"""Registry simples de serviços de domínio para composição das dependências."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, Optional, TypeVar

from fastapi import FastAPI

from src.shared.application.ports import ModuleRegistryPort

if TYPE_CHECKING:  # pragma: no cover - apenas para hints
    from src.media_management.bootstrap import MediaModule
    from src.user_management.bootstrap import UserManagementModule
else:
    MediaModule = Any  # type: ignore[assignment]
    UserManagementModule = Any  # type: ignore[assignment]


TModule = TypeVar("TModule")


@dataclass(slots=True)
class ModuleBinding(Generic[TModule]):
    """Stores the active module and an optional facade."""

    module: TModule
    facade: Optional[object] = None


@dataclass(slots=True)
class DomainServiceRegistry:
    """Aggregates bindings for the high-level domain modules."""

    user_management: ModuleBinding[UserManagementModule]
    media_management: ModuleBinding[MediaModule]
    media_processing: ModuleBinding[Optional[object]]
    text_analysis: ModuleBinding[Optional[object]]


def build_domain_service_registry(
    *,
    user_management: UserManagementModule,
    media_management: MediaModule,
    media_processing: object | None = None,
    text_analysis: object | None = None,
) -> DomainServiceRegistry:
    """Instantiate the registry with the current modules and optional facades."""
    return DomainServiceRegistry(
        user_management=ModuleBinding(module=user_management, facade=None),
        media_management=ModuleBinding(module=media_management, facade=None),
        media_processing=ModuleBinding(
            module=media_processing
            or getattr(media_management, "processing_service", None),
            facade=media_processing
            or getattr(media_management, "processing_service", None),
        ),
        text_analysis=ModuleBinding(
            module=text_analysis,
            facade=(
                getattr(text_analysis, "service", None)
                if text_analysis is not None
                else None
            ),
        ),
    )


class FastAPIModuleRegistry(ModuleRegistryPort):
    """Adapter to attach the domain service registry to FastAPI state."""

    def __init__(self, registry: DomainServiceRegistry) -> None:
        self._registry = registry

    def attach(self, app: FastAPI) -> None:
        app.state.domain_services = self._registry

    def get(self) -> DomainServiceRegistry:
        return self._registry


__all__ = [
    "DomainServiceRegistry",
    "ModuleBinding",
    "build_domain_service_registry",
    "FastAPIModuleRegistry",
]
