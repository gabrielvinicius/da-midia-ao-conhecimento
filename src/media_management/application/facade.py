"""High-level orchestrator exposing consolidated media operations."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

import structlog

from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.application.services import MediaService
from src.media_management.domain.enums import MediaStatus
from src.media_management.domain.media import Media
from src.shared.events.bus import SupportsEventBus
from src.shared.events.domain_events import MediaDeleted, MediaReprocessRequested
from src.storage.application.maintenance_service import StorageMaintenanceService
from src.user_management.domain.user import User, UserRole

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class MediaOrchestrator:
    """Entry point for administrative orchestration and event publication."""

    queries: MediaQueries
    media_service: MediaService
    event_bus: SupportsEventBus | None = None
    storage_factory: Any | None = None
    # Injected or instantiated lazily
    _storage_maintenance: StorageMaintenanceService | None = None

    def __post_init__(self):
        if self.storage_factory and not self._storage_maintenance:
            self._storage_maintenance = StorageMaintenanceService(self.storage_factory)

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
        if not self._storage_maintenance:
            logger.warning("media_management.facade.cleanup.missing_service")
            return 0

        # 1. Gather all known paths from DB
        provider_records: Dict[str, Set[str]] = {}
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
                if provider not in provider_records:
                    provider_records[provider] = set()
                
                # Normalize DB path to generic relative path if needed
                # Assuming DB stores relative paths like "videos/..."
                # If DB stores absolute paths, we strip the prefix or handle it here.
                # Current implementation assumes relative paths stored in DB match Storage paths.
                provider_records[provider].add(media.original_file_path)

            if len(batch) < page_size:
                break
            page += 1

        # 2. Delegate cleanup to StorageMaintenanceService
        total_deleted = 0
        # Ensure we check at least "local" even if DB is empty, to clean garbage
        providers = set(provider_records.keys())
        if not providers:
            providers.add("local")

        for provider in providers:
            known_files = provider_records.get(provider, set())
            
            deleted = await self._storage_maintenance.cleanup_orphaned_files(
                provider_name=provider,
                valid_files=known_files,
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