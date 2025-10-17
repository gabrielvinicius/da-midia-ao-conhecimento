# src/shared/application/services/file_service.py
"""
File Service implementation following SRP principle.
Responsible only for file operations.
"""
import os
import aiofiles
import structlog
from pathlib import Path

from src.shared.domain.interfaces import FileService as IFileService

logger = structlog.get_logger(__name__)


class FileService(IFileService):
    """
    File operations service implementation.
    Follows SRP: Only responsible for file I/O operations.
    """
    
    async def read_file(self, file_path: str) -> bytes:
        """Read file contents."""
        logger.info("file.read.started", file_path=file_path)
        
        try:
            async with aiofiles.open(file_path, 'rb') as file:
                content = await file.read()
            
            logger.info(
                "file.read.completed",
                file_path=file_path,
                size=len(content)
            )
            
            return content
            
        except FileNotFoundError:
            logger.error("file.read.not_found", file_path=file_path)
            raise
        except Exception as e:
            logger.error("file.read.failed", file_path=file_path, error=str(e))
            raise
    
    async def write_file(self, file_path: str, content: bytes) -> bool:
        """Write content to file."""
        logger.info(
            "file.write.started",
            file_path=file_path,
            size=len(content)
        )
        
        try:
            # Create directory if it doesn't exist
            directory = os.path.dirname(file_path)
            if directory:
                Path(directory).mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(file_path, 'wb') as file:
                await file.write(content)
            
            logger.info("file.write.completed", file_path=file_path)
            return True
            
        except Exception as e:
            logger.error("file.write.failed", file_path=file_path, error=str(e))
            raise
    
    async def delete_file(self, file_path: str) -> bool:
        """Delete file."""
        logger.info("file.delete.started", file_path=file_path)
        
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info("file.delete.completed", file_path=file_path)
                return True
            else:
                logger.warning("file.delete.not_found", file_path=file_path)
                return False
                
        except Exception as e:
            logger.error("file.delete.failed", file_path=file_path, error=str(e))
            raise
    
    async def file_exists(self, file_path: str) -> bool:
        """Check if file exists."""
        exists = os.path.exists(file_path)
        logger.debug("file.exists.checked", file_path=file_path, exists=exists)
        return exists