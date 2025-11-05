"""Registry that tracks domain services as we transition from legacy modules."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Generic, Optional, TypeVar
from uuid import UUID

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

def _build_media_processing_placeholder() -> MediaProcessingService:
    """Create a MediaProcessingService with lightweight no-op dependencies.

    During the lightweight bootstrap used in smoke tests we do not have the full
    processing stack wired. Providing a stub keeps the service registry backwards
    compatible without pulling heavy infrastructure.
    """

    class _NoOpTranscriptionService:
        async def request_transcription_generation(
            self,
            *,
            media_id: UUID | str,
            file_path: str,
            storage_provider: str,
            transcription_provider: str,
            language: str,
        ) -> Dict[str, Any]:  # type: ignore[type-var]
            return {
                "media_id": str(media_id),
                "file_path": file_path,
                "storage_provider": storage_provider,
                "provider": transcription_provider,
                "language": language,
                "status": "noop",
            }

        async def get_transcription_by_media_id(self, media_id: UUID | str):  # pragma: no cover - stub
            return None

    class _NoOpTranscriptionQueries:
        async def get_by_id(self, transcription_id: UUID | str):  # pragma: no cover - stub
            return None

    class _NoOpVideoService:
        async def request_video_processing(
            self,
            *,
            media_id: UUID | str,
            file_path: str,
            storage_provider: str,
        ) -> Dict[str, Any]:  # type: ignore[type-var]
            return {
                "media_id": str(media_id),
                "file_path": file_path,
                "storage_provider": storage_provider,
                "status": "noop",
            }

    return MediaProcessingService(
        transcription_service=_NoOpTranscriptionService(),  # type: ignore[arg-type]
        transcription_queries=_NoOpTranscriptionQueries(),  # type: ignore[arg-type]
        video_service=_NoOpVideoService(),  # type: ignore[arg-type]
    )


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
            facade=_build_media_processing_placeholder(),
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
