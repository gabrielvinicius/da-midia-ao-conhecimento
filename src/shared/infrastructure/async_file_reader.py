# src/shared/infrastructure/async_file_reader.py
"""Async File Reader Service - Single Responsibility Principle
Extracted from AsyncFileHandler God Class (350 lines)
Handles file reading operations and streaming
"""

import hashlib
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional

import aiofiles

from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("async_file_reader")


class AsyncFileReader:
    """Async file reading with Single Responsibility:
    Handle file reading operations, streaming, and content analysis
    """

    CHUNK_SIZE = 64 * 1024  # 64KB chunks for streaming
    BUFFER_SIZE = 8 * 1024 * 1024  # 8MB buffer for large operations

    def __init__(self, chunk_size: int = None):
        self.chunk_size = chunk_size or self.CHUNK_SIZE

    async def read_file_chunks(
        self,
        file_path: str,
        chunk_size: Optional[int] = None
    ) -> AsyncGenerator[bytes, None]:
        """Read file in async chunks for efficient streaming
        
        Args:
            file_path: Path to the file
            chunk_size: Chunk size in bytes
            
        Yields:
            File data chunks

        """
        effective_chunk_size = chunk_size or self.chunk_size

        try:
            async with aiofiles.open(file_path, 'rb') as file:
                while chunk := await file.read(effective_chunk_size):
                    yield chunk

        except FileNotFoundError:
            logger.error("File not found for streaming", file_path=file_path)
            raise
        except Exception as e:
            logger.error("Error streaming file", file_path=file_path, error=str(e))
            raise

    async def read_file_complete(self, file_path: str) -> bytes:
        """Read complete file content into memory
        
        Args:
            file_path: Path to the file
            
        Returns:
            Complete file content as bytes

        """
        try:
            async with aiofiles.open(file_path, 'rb') as file:
                content = await file.read()

            logger.debug("File read completely", file_path=file_path, size=len(content))
            return content

        except Exception as e:
            logger.error("Error reading file", file_path=file_path, error=str(e))
            raise

    async def read_file_lines(self, file_path: str, encoding: str = 'utf-8') -> AsyncGenerator[str, None]:
        """Read file line by line asynchronously
        
        Args:
            file_path: Path to the file
            encoding: File encoding
            
        Yields:
            File lines

        """
        try:
            async with aiofiles.open(file_path, 'r', encoding=encoding) as file:
                async for line in file:
                    yield line.rstrip('\n\r')

        except Exception as e:
            logger.error("Error reading file lines", file_path=file_path, error=str(e))
            raise

    async def get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get comprehensive file information
        
        Args:
            file_path: Path to the file
            
        Returns:
            File information dictionary

        """
        try:
            import mimetypes
            from datetime import datetime

            path_obj = Path(file_path)

            if not path_obj.exists():
                raise FileNotFoundError(f"File not found: {file_path}")

            stat_info = path_obj.stat()
            mime_type, _ = mimetypes.guess_type(file_path)

            file_info = {
                "path": str(path_obj.absolute()),
                "name": path_obj.name,
                "stem": path_obj.stem,
                "suffix": path_obj.suffix,
                "size": stat_info.st_size,
                "size_mb": round(stat_info.st_size / (1024 * 1024), 2),
                "mime_type": mime_type,
                "created_at": datetime.fromtimestamp(stat_info.st_ctime),
                "modified_at": datetime.fromtimestamp(stat_info.st_mtime),
                "accessed_at": datetime.fromtimestamp(stat_info.st_atime),
                "is_file": path_obj.is_file(),
                "is_readable": path_obj.exists() and stat_info.st_mode & 0o444
            }

            return file_info

        except Exception as e:
            logger.error("Error getting file info", file_path=file_path, error=str(e))
            raise

    async def calculate_file_hash(self, file_path: str, algorithm: str = 'md5') -> str:
        """Calculate file hash asynchronously
        
        Args:
            file_path: Path to the file
            algorithm: Hash algorithm (md5, sha1, sha256)
            
        Returns:
            File hash string

        """
        try:
            if algorithm == 'md5':
                hasher = hashlib.md5()
            elif algorithm == 'sha1':
                hasher = hashlib.sha1()
            elif algorithm == 'sha256':
                hasher = hashlib.sha256()
            else:
                raise ValueError(f"Unsupported hash algorithm: {algorithm}")

            async with aiofiles.open(file_path, 'rb') as file:
                while chunk := await file.read(self.chunk_size):
                    hasher.update(chunk)

            file_hash = hasher.hexdigest()

            logger.debug("File hash calculated",
                        file_path=file_path,
                        algorithm=algorithm,
                        hash=file_hash[:16] + "...")

            return file_hash

        except Exception as e:
            logger.error("Error calculating file hash",
                        file_path=file_path,
                        algorithm=algorithm,
                        error=str(e))
            raise

    async def validate_file_integrity(self, file_path: str, expected_hash: str, algorithm: str = 'md5') -> bool:
        """Validate file integrity using hash comparison
        
        Args:
            file_path: Path to the file
            expected_hash: Expected hash value
            algorithm: Hash algorithm
            
        Returns:
            True if file is valid, False otherwise

        """
        try:
            actual_hash = await self.calculate_file_hash(file_path, algorithm)
            is_valid = actual_hash.lower() == expected_hash.lower()

            if is_valid:
                logger.info("File integrity validation passed", file_path=file_path)
            else:
                logger.warning("File integrity validation failed",
                             file_path=file_path,
                             expected=expected_hash[:16] + "...",
                             actual=actual_hash[:16] + "...")

            return is_valid

        except Exception as e:
            logger.error("Error validating file integrity",
                        file_path=file_path,
                        error=str(e))
            return False

    async def check_file_exists(self, file_path: str) -> bool:
        """Check if file exists asynchronously
        
        Args:
            file_path: Path to check
            
        Returns:
            True if file exists, False otherwise

        """
        try:
            import aiofiles.os
            await aiofiles.os.stat(file_path)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            logger.error("Error checking file existence", file_path=file_path, error=str(e))
            return False

    async def get_file_size(self, file_path: str) -> int:
        """Get file size asynchronously
        
        Args:
            file_path: Path to the file
            
        Returns:
            File size in bytes

        """
        try:
            import aiofiles.os
            stat_info = await aiofiles.os.stat(file_path)
            return stat_info.st_size

        except Exception as e:
            logger.error("Error getting file size", file_path=file_path, error=str(e))
            raise

    def set_chunk_size(self, chunk_size: int):
        """Set default chunk size for reading operations
        
        Args:
            chunk_size: New chunk size in bytes

        """
        self.chunk_size = chunk_size
        logger.info("Chunk size updated", chunk_size=chunk_size)

    def get_reading_stats(self) -> Dict[str, Any]:
        """Get reading configuration stats
        
        Returns:
            Configuration information

        """
        return {
            "chunk_size": self.chunk_size,
            "chunk_size_kb": self.chunk_size / 1024,
            "buffer_size": self.BUFFER_SIZE,
            "buffer_size_mb": self.BUFFER_SIZE / (1024 * 1024)
        }


# Default instance
async_file_reader = AsyncFileReader()
