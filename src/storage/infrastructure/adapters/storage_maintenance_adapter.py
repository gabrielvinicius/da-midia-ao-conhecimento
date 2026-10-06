from __future__ import annotations

from src.storage.application.services.maintenance_service import StorageMaintenancePort
from src.storage.infrastructure.dependencies import StorageServiceFactory


class StorageMaintenanceAdapter(StorageMaintenancePort):
    def __init__(self, factory: StorageServiceFactory):
        self._factory = factory

    async def delete(self, provider_name: str, path: str) -> None:
        service = self._factory.create_storage_service(provider_name)
        await service.delete(path)

    async def delete_folder(self, provider_name: str, folder_path: str) -> None:
        service = self._factory.create_storage_service(provider_name)
        await service.delete_folder(folder_path)


__all__ = ["StorageMaintenanceAdapter"]
