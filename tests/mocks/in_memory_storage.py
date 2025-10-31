# tests/mocks/in_memory_storage.py
"""
Enhanced in-memory storage service for comprehensive testing.
"""
from typing import Dict, Optional, Tuple, List
from src.storage.application.storage_service import StorageService


class InMemoryStorage(StorageService):
    """Enhanced in-memory storage with testing utilities."""
    
    def __init__(self):
        self.files: Dict[str, bytes] = {}
        self.metadata: Dict[str, dict] = {}
        self.upload_count = 0
        self.download_count = 0

    async def upload(self, file_path: str, file: bytes) -> None:
        """Store file content in memory."""
        self.upload_count += 1
        self.files[file_path] = file
        self.metadata[file_path] = {
            "size": len(file),
            "content_type": "application/octet-stream"
        }

    async def download(self, file_path: str) -> Optional[Tuple[bytes, str]]:
        """Retrieve file content from memory."""
        self.download_count += 1
        file_content = self.files.get(file_path)
        if file_content:
            return file_content, file_path.split("/")[-1]
        return None

    async def delete(self, file_path: str) -> bool:
        """Remove file from memory storage."""
        if file_path in self.files:
            del self.files[file_path]
            if file_path in self.metadata:
                del self.metadata[file_path]
            return True
        return False

    async def exists(self, file_path: str) -> bool:
        """Check if file exists in memory storage."""
        return file_path in self.files
    
    def clear(self):
        """Clear all stored files (useful for test cleanup)."""
        self.files.clear()
        self.metadata.clear()
        self.upload_count = 0
        self.download_count = 0
    
    def get_stats(self) -> dict:
        """Get storage statistics for testing."""
        return {
            "files_count": len(self.files),
            "total_size": sum(len(content) for content in self.files.values()),
            "upload_count": self.upload_count,
            "download_count": self.download_count
        }


# Alias for backward compatibility
InMemoryStorageService = InMemoryStorage
