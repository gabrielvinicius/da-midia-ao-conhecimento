"""Registry that tracks domain services as we transition from legacy modules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, Optional, TYPE_CHECKING, TypeVar

from fastapi import FastAPI

from src.media_processing import MediaProcessingService
from src.text_analysis import TextAnalysisService

if TYPE_CHECKING:  # pragma: no cover - apenas para hints
    from src.media_management.bootstrap import MediaModule
    from src.user_management.bootstrap import UserManagementModule
else:
    MediaModule = Any  # type: ignore[assignment]
    UserManagementModule = Any  # type: ignore[assignment]


TLegacy = TypeVar("TLegacy")


@dataclass(slots=True)
class ModuleBinding(Generic[TLegacy]):
    """Stores the legacy module and the new facade placeholder."""

    legacy: TLegacy
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
) -> DomainServiceRegistry:
    """Instantiate the registry with legacy modules and placeholder facades."""

    return DomainServiceRegistry(
        user_management=ModuleBinding(
            legacy=user_management,
            facade=None,  # Stage C1 will provide an explicit UserManagementService facade
        ),
        media_management=ModuleBinding(
            legacy=media_management,
            facade=None,  # Stage C2 will populate with a MediaManagementService facade
        ),
        media_processing=ModuleBinding(
            legacy=None,
            facade=MediaProcessingService(),
        ),
        text_analysis=ModuleBinding(
            legacy=None,
            facade=TextAnalysisService(),
        ),
    )


def attach_domain_services(app: FastAPI, registry: DomainServiceRegistry) -> None:
    """Expose the registry through the FastAPI application state for diagnostics."""

    app.state.domain_services = registry


__all__ = [
    "DomainServiceRegistry",
    "ModuleBinding",
    "attach_domain_services",
    "build_domain_service_registry",
]
