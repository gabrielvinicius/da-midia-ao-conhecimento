"""Service for storage maintenance tasks like cleanup and consistency checks."""
from __future__ import annotations

from typing import List, Protocol, Set

import structlog

from src.storage.application.ports import FileReferenceValidatorPort

logger = structlog.get_logger(__name__)


class StorageMaintenancePort(Protocol):
    """Port exposing minimal storage operations required for maintenance."""

    async def list_files(self, provider_name: str) -> list[str]: ...

    async def delete(self, provider_name: str, path: str) -> None: ...

    async def delete_folder(self, provider_name: str, folder_path: str) -> None: ...


class StorageMaintenanceService:
    """Handles storage maintenance operations such as cleaning up orphaned files."""

    def __init__(self, storage_port: StorageMaintenancePort) -> None:
        self._storage = storage_port
        self._validators: List[FileReferenceValidatorPort] = []

    def register_validator(self, validator: FileReferenceValidatorPort) -> None:
        """Registers a new validator that can vouch for file existence."""
        self._validators.append(validator)

    async def delete_file(self, provider_name: str, path: str) -> None:
        """Delete a single file, used by higher-level services (e.g., media delete)."""
        await self._storage.delete(provider_name, path)

    async def delete_folder(self, provider_name: str, folder_path: str) -> None:
        """Delete an entire folder/prefix, useful for deep media cleanup."""
        await self._storage.delete_folder(provider_name, folder_path)

    async def cleanup_orphaned_files(
        self,
        provider_name: str,
        dry_run: bool = False,
    ) -> int:
        """Identifies and removes files in storage that are not claimed by any validator.

        Args:
            provider_name: The storage provider to clean (e.g., 'local', 's3').
            dry_run: If True, only logs what would be deleted.

        Returns:
            Count of deleted files.
        """
        try:
            stored_files = await self._storage.list_files(provider_name)
            
            # Normalize paths
            candidates = {f.replace("\\", "/") for f in stored_files}
            valid_files: Set[str] = set()

            # Ask all validators which files they know about
            for validator in self._validators:
                try:
                    claimed = await validator.validate_batch(provider_name, list(candidates))
                    valid_files.update(claimed)
                except Exception as exc:
                    logger.error(
                        "storage.cleanup.validator_failed",
                        provider=provider_name,
                        error=str(exc),
                    )
                    # If a validator fails, we abort to avoid deleting valid files
                    return 0

            orphans = candidates - valid_files
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
