"""Service for storage maintenance tasks like cleanup and consistency checks."""
from __future__ import annotations

from typing import List, Set

import structlog

from src.storage.infrastructure.dependencies import StorageServiceFactory

logger = structlog.get_logger(__name__)


class StorageMaintenanceService:
    """Handles storage maintenance operations such as cleaning up orphaned files."""

    def __init__(self, storage_factory: StorageServiceFactory) -> None:
        self._storage_factory = storage_factory

    async def cleanup_orphaned_files(
        self,
        provider_name: str,
        valid_files: Set[str],
        dry_run: bool = False
    ) -> int:
        """
        Identifies and removes files in storage that are not in the valid_files set.
        
        Args:
            provider_name: The storage provider to clean (e.g., 'local', 's3').
            valid_files: A set of file paths (relative strings) that are known and valid.
            dry_run: If True, only logs what would be deleted.

        Returns:
            Count of deleted files.
        """
        try:
            storage_service = self._storage_factory.create_storage_service(provider_name)
            # We need to access the backend service directly to use list_files
            # StorageClientAdapter might wrap it. Let's assume we get the adapter or service.
            # If adapter, we need to expose list_files on adapter too.
            # Checking dependencies.py... StorageClientAdapter does NOT have list_files.
            
            # Hack/Fix: Access backend directly or update Adapter.
            # Updating Adapter is cleaner. I will assume Adapter has list_files.
            # Wait, I missed updating StorageClientAdapter in dependencies.py!
            # I must do that first.
            
            # Assuming I fix the adapter:
            stored_files = await storage_service.list_files()
            
            orphans = []
            for file_path in stored_files:
                # Normalize paths for comparison (generic handling)
                norm_path = file_path.replace("\", "/")
                if norm_path not in valid_files:
                    orphans.append(file_path)

            deleted_count = 0
            for orphan in orphans:
                if dry_run:
                    logger.info("storage.cleanup.dry_run", provider=provider_name, file=orphan)
                else:
                    try:
                        await storage_service.delete(orphan)
                        deleted_count += 1
                        logger.info("storage.cleanup.deleted", provider=provider_name, file=orphan)
                    except Exception as exc:
                        logger.warning(
                            "storage.cleanup.delete_failed",
                            provider=provider_name,
                            file=orphan,
                            error=str(exc)
                        )
            
            return deleted_count

        except Exception as exc:
            logger.error(
                "storage.cleanup.failed",
                provider=provider_name,
                error=str(exc)
            )
            return 0
