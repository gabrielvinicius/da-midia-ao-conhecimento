"""High-level orchestrator exposing consolidated media operations."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

import structlog

from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.application.services import MediaService
from src.media_management.domain.enums import MediaStatus
from src.media_management.domain.media import Media
from src.shared.events.bus import SupportsEventBus
from src.shared.events.domain_events import MediaDeleted, MediaReprocessRequested
from src.user_management.domain.user import User, UserRole

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class MediaOrchestrator:
    """Entry point for administrative orchestration and event publication."""

    queries: MediaQueries
    media_service: MediaService
    event_bus: SupportsEventBus | None = None
    storage_factory: Any | None = None

    async def _publish_event(self, event) -> None:
        """Safely publish domain events without breaking the request flow."""
        if self.event_bus is None:
            return
        try:
            await self.event_bus.publish(event)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "media_management.facade.event_publish_failed",
                event_type=type(event).__name__,
                error=str(exc),
            )

    def _resolve_storage_root(self, provider: str) -> Optional[Path]:
        """Resolve the filesystem root for the given storage provider."""
        if self.storage_factory is None:
            return None

        resolver = getattr(self.storage_factory, "get_provider_root", None)
        if resolver is None:
            return None

        try:
            root = resolver(provider)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                "media_management.facade.storage_root_resolution_failed",
                provider=provider,
                error=str(exc),
            )
            return None

        return Path(root)

    @staticmethod
    def _normalise_media_path(raw_path: str, base_dir: Path) -> Optional[Path]:
        """Convert a stored media path to an absolute filesystem Path under base_dir."""
        if not raw_path:
            return None

        raw_path = raw_path.strip()
        if not raw_path:
            return None

        candidate = Path(raw_path)
        if candidate.is_absolute():
            abs_candidate = candidate.resolve(strict=False)
            if abs_candidate == base_dir or base_dir in abs_candidate.parents:
                return abs_candidate
            return None

        normalised = raw_path.replace("\\", "/")
        while normalised.startswith("./"):
            normalised = normalised[2:]
        normalised = normalised.lstrip("/")

        prefixes = (
            "storage/",
            f"{base_dir.parent.name}/",
            f"{base_dir.name}/",
        )
        for prefix in prefixes:
            if normalised.startswith(prefix):
                normalised = normalised[len(prefix):]

        if normalised.startswith("media/"):
            normalised = normalised[len("media/"):]

        if not normalised:
            return None

        return (base_dir / normalised).resolve(strict=False)

    @staticmethod
    def _gather_media_files(base_dir: Path) -> List[Path]:
        """Return all files located under the given media base directory."""
        if not base_dir.exists():
            return []

        return [
            path.resolve(strict=False)
            for path in base_dir.rglob("*")
            if path.is_file()
        ]

    @staticmethod
    def _prune_empty_directories(directories: Set[Path], stop_at: Path) -> None:
        """Remove empty directories left after deleting orphan files."""
        for directory in sorted(directories, key=lambda p: len(p.parts), reverse=True):
            if directory == stop_at:
                continue
            if not directory.exists():
                continue
            try:
                resolved = directory.resolve(strict=False)
                if stop_at not in resolved.parents and resolved != stop_at:
                    continue
            except Exception:  # pragma: no cover - defensive guard
                continue
            try:
                directory.rmdir()
            except OSError:
                # Directory not empty or cannot be removed; ignore
                continue

    async def _cleanup_provider_storage(
        self,
        *,
        provider: str,
        base_dir: Path,
        known_files: Set[Path],
    ) -> int:
        """Delete orphaned files from the provider media directory."""
        media_files = await asyncio.to_thread(self._gather_media_files, base_dir)
        if not media_files:
            return 0

        deleted: List[Path] = []
        known_files_normalised = {path.resolve(strict=False) for path in known_files}

        for file_path in media_files:
            if known_files_normalised and file_path in known_files_normalised:
                continue
            try:
                await asyncio.to_thread(file_path.unlink)
                deleted.append(file_path)
            except FileNotFoundError:  # pragma: no cover - race condition
                continue
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning(
                    "media_management.facade.cleanup_orphaned_files.unlink_failed",
                    provider=provider,
                    path=str(file_path),
                    error=str(exc),
                )

        if deleted:
            directories = {path.parent for path in deleted}
            await asyncio.to_thread(self._prune_empty_directories, directories, base_dir)

        return len(deleted)

    async def delete_media_as_admin(
        self,
        *,
        media_id: UUID,
        actor_id: Optional[str] = None,
        triggered_by: str = "admin",
    ) -> None:
        media = await self.media_service.delete_media(
            media_id=media_id,
            user_id=None,
            user_role=UserRole.ADMIN,
        )

        await self._publish_event(
            MediaDeleted(
                media_id=str(media_id),
                user_id=str(media.user_id),
                triggered_by=triggered_by,
                actor_id=actor_id,
            )
        )

    async def reprocess_media_as_admin(
        self,
        *,
        media_id: UUID,
        actor_id: Optional[str] = None,
        triggered_by: str = "admin",
    ) -> None:
        await self.media_service.reprocess_media(
            media_id=media_id,
            user_id=None,
            user_role=UserRole.ADMIN,
        )
        await self._publish_event(
            MediaReprocessRequested(
                media_id=str(media_id),
                triggered_by=triggered_by,
                actor_id=actor_id,
            )
        )

    async def bulk_reprocess_failed_media(
        self,
        *,
        candidates: Optional[List[Media]] = None,
        actor_id: Optional[str] = None,
    ) -> int:
        media_list = candidates or await self.queries.list_all(
            status=MediaStatus.FAILED,
            limit=10_000,
        )
        processed = 0
        for media in media_list:
            try:
                await self.reprocess_media_as_admin(
                    media_id=media.id,
                    actor_id=actor_id,
                    triggered_by="admin_bulk",
                )
                processed += 1
            except Exception as exc:  # pragma: no cover - defensive logging path
                logger.warning(
                    "media_management.facade.bulk_reprocess_failed",
                    media_id=str(media.id),
                    error=str(exc),
                )
        return processed

    async def cleanup_orphaned_files(
        self,
        *,
        actor_id: Optional[str] = None,
    ) -> int:
        provider_records: Dict[str, List[str]] = {}

        page = 1
        page_size = 500
        total_records = 0

        while True:
            batch = await self.queries.list_all(page=page, limit=page_size)
            if not batch:
                break

            total_records += len(batch)
            for media in batch:
                provider = (media.storage_provider or "local").lower()
                provider_records.setdefault(provider, []).append(media.original_file_path)

            if len(batch) < page_size:
                break
            page += 1

        providers: Set[str] = set(provider_records.keys())
        if not providers:
            providers.add("local")

        total_deleted = 0

        for provider in providers:
            root = self._resolve_storage_root(provider)
            if root is None:
                logger.warning(
                    "media_management.facade.cleanup_orphaned_files.root_missing",
                    provider=provider,
                )
                continue

            base_dir = (root / "media").resolve(strict=False)
            known_paths_raw = provider_records.get(provider, [])
            known_files: Set[Path] = set()
            for raw_path in known_paths_raw:
                normalised = self._normalise_media_path(raw_path, base_dir)
                if normalised is not None:
                    known_files.add(normalised)

            deleted = await self._cleanup_provider_storage(
                provider=provider,
                base_dir=base_dir,
                known_files=known_files,
            )
            total_deleted += deleted

            logger.info(
                "media_management.facade.cleanup_orphaned_files.provider_summary",
                provider=provider,
                deleted=deleted,
                known_files=len(known_files),
                actor_id=actor_id,
            )

        logger.info(
            "media_management.facade.cleanup_orphaned_files.summary",
            deleted=total_deleted,
            scanned_records=total_records,
            actor_id=actor_id,
        )

        return total_deleted

    async def delete_media_for_user(self, *, media_id: UUID, acting_user: User) -> None:
        media = await self.media_service.delete_media(
            media_id=media_id,
            user_id=acting_user.id,
            user_role=acting_user.role,
        )
        await self._publish_event(MediaDeleted.for_user(media, acting_user.id))

    async def reprocess_media_for_user(self, *, media_id: UUID, acting_user: User) -> None:
        await self.media_service.reprocess_media(
            media_id=media_id,
            user_id=acting_user.id,
            user_role=acting_user.role,
        )
        await self._publish_event(MediaReprocessRequested.for_user(media_id, acting_user.id))
