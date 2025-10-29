# src/shared/infrastructure/async_file_writer.py
"""
Async File Writer Service - Single Responsibility Principle
Extracted from AsyncFileHandler God Class (350 lines)
Handles file writing operations and temporary file management
"""

import aiofiles
import aiofiles.os
import asyncio
from typing import Optional, AsyncGenerator, Dict, Any
from pathlib import Path
import hashlib
import tempfile
from datetime import datetime

from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("async_file_writer")


class AsyncFileWriter:
    """
    Async file writing with Single Responsibility:
    Handle file writing operations, streaming writes, and temporary file management
    """
    
    CHUNK_SIZE = 64 * 1024  # 64KB chunks for streaming
    
    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = Path(temp_dir) if temp_dir else Path("/tmp/media_processing")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    async def write_file_from_stream(
        self, 
        file_path: str, 
        data_stream: AsyncGenerator[bytes, None],
        expected_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Write file from async stream with validation
        
        Args:
            file_path: Destination path
            data_stream: Data stream
            expected_size: Expected size for validation
            
        Returns:
            Dictionary with saved file information
        """
        file_path_obj = Path(file_path)
        file_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        written_bytes = 0
        hash_md5 = hashlib.md5()
        
        try:
            async with aiofiles.open(file_path, 'wb') as file:
                async for chunk in data_stream:
                    await file.write(chunk)
                    written_bytes += len(chunk)
                    hash_md5.update(chunk)
                    
                    # Check size limit if provided
                    if expected_size and written_bytes > expected_size * 1.1:  # 10% tolerance
                        raise ValueError(f"File size exceeded expected size: {written_bytes} > {expected_size}")
            
            # Validate final size
            if expected_size and abs(written_bytes - expected_size) > expected_size * 0.05:  # 5% tolerance
                await aiofiles.os.remove(file_path)
                raise ValueError(f"File size mismatch: expected {expected_size}, got {written_bytes}")
            
            # Get file stats
            file_stats = await aiofiles.os.stat(file_path)
            
            result = {
                "file_path": file_path,
                "size": file_stats.st_size,
                "written_bytes": written_bytes,
                "md5_hash": hash_md5.hexdigest(),
                "created_at": datetime.utcnow(),
                "validated": expected_size is not None
            }
            
            logger.info("File written from stream", **{k: v for k, v in result.items() if k != 'md5_hash'})
            return result
            
        except Exception as e:
            # Clean up partial file
            try:
                await aiofiles.os.remove(file_path)
            except:
                pass
            
            logger.error("Error writing file from stream", 
                        file_path=file_path, 
                        written_bytes=written_bytes, 
                        error=str(e))
            raise
    
    async def write_file_complete(self, file_path: str, content: bytes) -> Dict[str, Any]:
        """
        Write complete file content
        
        Args:
            file_path: Destination path
            content: File content
            
        Returns:
            Dictionary with saved file information
        """
        try:
            file_path_obj = Path(file_path)
            file_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(file_path, 'wb') as file:
                await file.write(content)
            
            # Calculate hash
            hash_md5 = hashlib.md5(content).hexdigest()
            
            # Get file stats
            file_stats = await aiofiles.os.stat(file_path)
            
            result = {
                "file_path": file_path,
                "size": len(content),
                "md5_hash": hash_md5,
                "created_at": datetime.utcnow()
            }
            
            logger.info("File written completely", file_path=file_path, size=len(content))
            return result
            
        except Exception as e:
            logger.error("Error writing file", file_path=file_path, error=str(e))
            raise
    
    async def append_to_file(self, file_path: str, content: bytes) -> Dict[str, Any]:
        """
        Append content to existing file
        
        Args:
            file_path: File path
            content: Content to append
            
        Returns:
            Dictionary with operation information
        """
        try:
            file_path_obj = Path(file_path)
            file_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Get original size if file exists
            original_size = 0
            if file_path_obj.exists():
                original_stats = await aiofiles.os.stat(file_path)
                original_size = original_stats.st_size
            
            async with aiofiles.open(file_path, 'ab') as file:
                await file.write(content)
            
            # Get new stats
            new_stats = await aiofiles.os.stat(file_path)
            
            result = {
                "file_path": file_path,
                "original_size": original_size,
                "appended_size": len(content),
                "final_size": new_stats.st_size,
                "appended_at": datetime.utcnow()
            }
            
            logger.info("Content appended to file", **result)
            return result
            
        except Exception as e:
            logger.error("Error appending to file", file_path=file_path, error=str(e))
            raise
    
    async def create_temp_file(self, content: bytes, suffix: str = "", prefix: str = "temp_") -> str:
        """
        Create temporary file with content
        
        Args:
            content: File content
            suffix: File suffix
            prefix: File prefix
            
        Returns:
            Temporary file path
        """
        try:
            # Generate unique filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            hash_part = hashlib.md5(content[:1024] if len(content) > 1024 else content).hexdigest()[:8]
            filename = f"{prefix}{timestamp}_{hash_part}{suffix}"
            
            temp_path = self.temp_dir / filename
            
            async with aiofiles.open(temp_path, 'wb') as file:
                await file.write(content)
            
            logger.debug("Temporary file created", path=str(temp_path), size=len(content))
            return str(temp_path)
            
        except Exception as e:
            logger.error("Error creating temporary file", error=str(e))
            raise
    
    async def create_temp_file_from_stream(
        self, 
        data_stream: AsyncGenerator[bytes, None], 
        suffix: str = "", 
        prefix: str = "temp_"
    ) -> str:
        """
        Create temporary file from data stream
        
        Args:
            data_stream: Data stream
            suffix: File suffix
            prefix: File prefix
            
        Returns:
            Temporary file path
        """
        try:
            # Generate unique filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}{timestamp}{suffix}"
            temp_path = self.temp_dir / filename
            
            written_bytes = 0
            async with aiofiles.open(temp_path, 'wb') as file:
                async for chunk in data_stream:
                    await file.write(chunk)
                    written_bytes += len(chunk)
            
            logger.debug("Temporary file created from stream", 
                        path=str(temp_path), 
                        size=written_bytes)
            return str(temp_path)
            
        except Exception as e:
            logger.error("Error creating temporary file from stream", error=str(e))
            raise
    
    async def cleanup_temp_files(self, max_age_hours: int = 24) -> int:
        """
        Clean up old temporary files
        
        Args:
            max_age_hours: Maximum age in hours
            
        Returns:
            Number of files removed
        """
        removed_count = 0
        max_age_seconds = max_age_hours * 3600
        current_time = datetime.utcnow().timestamp()
        
        try:
            for file_path in self.temp_dir.glob("temp_*"):
                try:
                    file_stats = await aiofiles.os.stat(file_path)
                    file_age = current_time - file_stats.st_ctime
                    
                    if file_age > max_age_seconds:
                        await aiofiles.os.remove(file_path)
                        removed_count += 1
                        
                except Exception as e:
                    logger.warning("Error removing temp file", file_path=str(file_path), error=str(e))
                    continue
            
            if removed_count > 0:
                logger.info("Temporary files cleaned up", removed_count=removed_count)
            
        except Exception as e:
            logger.error("Error cleaning up temp files", error=str(e))
        
        return removed_count
    
    async def get_temp_dir_stats(self) -> Dict[str, Any]:
        """
        Get temporary directory statistics
        
        Returns:
            Directory statistics
        """
        try:
            file_count = 0
            total_size = 0
            oldest_file = None
            newest_file = None
            
            for file_path in self.temp_dir.glob("temp_*"):
                try:
                    file_stats = await aiofiles.os.stat(file_path)
                    file_count += 1
                    total_size += file_stats.st_size
                    
                    if oldest_file is None or file_stats.st_ctime < oldest_file:
                        oldest_file = file_stats.st_ctime
                    
                    if newest_file is None or file_stats.st_ctime > newest_file:
                        newest_file = file_stats.st_ctime
                        
                except Exception:
                    continue
            
            return {
                "temp_dir": str(self.temp_dir),
                "file_count": file_count,
                "total_size": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "oldest_file_age_hours": (datetime.utcnow().timestamp() - oldest_file) / 3600 if oldest_file else None,
                "newest_file_age_hours": (datetime.utcnow().timestamp() - newest_file) / 3600 if newest_file else None
            }
            
        except Exception as e:
            logger.error("Error getting temp dir stats", error=str(e))
            return {"error": str(e)}
    
    def set_temp_dir(self, temp_dir: str):
        """
        Set temporary directory
        
        Args:
            temp_dir: New temporary directory path
        """
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Temporary directory updated", temp_dir=str(self.temp_dir))
    
    def get_writer_config(self) -> Dict[str, Any]:
        """
        Get writer configuration
        
        Returns:
            Configuration information
        """
        return {
            "temp_dir": str(self.temp_dir),
            "chunk_size": self.CHUNK_SIZE,
            "chunk_size_kb": self.CHUNK_SIZE / 1024
        }


# Default instance
async_file_writer = AsyncFileWriter()