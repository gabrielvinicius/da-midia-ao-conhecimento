"""Service for storage maintenance tasks like cleanup and consistency checks."""
from __future__ import annotations

from typing import Protocol, Set

import structlog

logger = structlog.get_logger(__name__)


class StorageMaintenancePort(Protocol):
    """Port exposing minimal storage operations required for maintenance."""

    async def list_files(self, provider_name: str) -> list[str]: ...

    async def delete(self, provider_name: str, path: str) -> None: ...


class StorageMaintenanceService:
    """Handles storage maintenance operations such as cleaning up orphaned files."""

    def __init__(self, storage_port: StorageMaintenancePort) -> None:
        self._storage = storage_port

    async def delete_file(self, provider_name: str, path: str) -> None:
        """Delete a single file, used by higher-level services (e.g., media delete)."""
        await self._storage.delete(provider_name, path)

    async def cleanup_orphaned_files(
        self,
        provider_name: str,
        valid_files: Set[str],
        dry_run: bool = False,
    ) -> int:
        """Identifies and removes files in storage that are not in the valid_files set.

        Args:
            provider_name: The storage provider to clean (e.g., 'local', 's3').
            valid_files: Set of file paths (relative strings) that are known and valid.
            dry_run: If True, only logs what would be deleted.

        Returns:
            Count of deleted files.

        """
        try:
            stored_files = await self._storage.list_files(provider_name)

            orphans = []
            for file_path in stored_files:
                # Normalize paths for comparison (generic handling)
                norm_path = file_path.replace("\\", "/")
                if norm_path not in valid_files:
                    orphans.append(file_path)

            deleted_count = 0
            for orphan in orphans:
                if dry_run:
                    logger.info(
                        "storage.cleanup.dry_run",
                        provider=provider_name,
                        file=orphan,
                    )
                else:
                    try:
                        await self._storage.delete(provider_name, orphan)
                        deleted_count += 1
                        logger.info(
                            "storage.cleanup.deleted",
                            provider=provider_name,
                            file=orphan,
                        )
                    except Exception as exc:
                        logger.warning(
                            "storage.cleanup.delete_failed",
                            provider=provider_name,
                            file=orphan,
                            error=str(exc),
                        )

            return deleted_count

        except Exception as exc:
            logger.error(
                "storage.cleanup.failed",
                provider=provider_name,
                error=str(exc),
            )
            return 0
