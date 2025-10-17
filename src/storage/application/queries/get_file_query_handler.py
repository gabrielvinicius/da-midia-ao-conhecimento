# src/storage/application/queries/get_file_query_handler.py
"""
Query handler for file retrieval following SOLID principles.
"""
from typing import Optional, Tuple

from src.storage.application.queries.get_file_query import GetFileQuery
from src.storage.domain.interfaces import StorageRepository
from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.value_objects.file_path import FilePath


class FileQueryResult:
    """Result object for file queries - SRP compliance."""
    
    def __init__(
        self, 
        content: Optional[bytes] = None, 
        metadata: Optional[FileMetadata] = None
    ):
        self.content = content
        self.metadata = metadata
        self.exists = metadata is not None


class GetFileQueryHandler:
    """
    Query handler for file retrieval following SOLID principles.
    SRP: Only handles file query processing.
    DIP: Depends on abstractions, not concretions.
    """
    
    def __init__(self, storage_repository: StorageRepository):
        self._storage_repository = storage_repository
    
    async def handle(self, query: GetFileQuery) -> FileQueryResult:
        """Handle file retrieval query."""
        file_path = FilePath.from_path(query.file_path)
        
        # Get metadata first
        metadata = await self._storage_repository.get_metadata(file_path)
        
        if not metadata:
            return FileQueryResult()
        
        # Get content if requested
        content = None
        if query.include_content:
            content = await self._storage_repository.retrieve(file_path)
        
        return FileQueryResult(content=content, metadata=metadata)