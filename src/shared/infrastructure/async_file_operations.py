# src/shared/infrastructure/async_file_operations.py
"""Async File Operations Service - Single Responsibility Principle
Extracted from AsyncFileHandler God Class (350 lines)
Handles advanced file operations like copying, moving, and validation
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import aiofiles
import aiofiles.os

from src.shared.infrastructure.logging_config import get_logger

from .async_file_reader import AsyncFileReader, async_file_reader

logger = get_logger("async_file_operations")


class AsyncFileOperations:
    """Advanced file operations with Single Responsibility:
    Handle file copying, moving, deletion, and advanced operations
    """

    CHUNK_SIZE = 64 * 1024  # 64KB chunks for operations

    def __init__(self, file_reader: Optional[AsyncFileReader] = None):
        self.file_reader = file_reader or async_file_reader

    async def copy_file_async(
        self,
        source_path: str,
        dest_path: str,
        verify_checksum: bool = True,
        overwrite: bool = False
    ) -> Dict[str, Any]:
        """Copy file asynchronously with integrity verification
        
        Args:
            source_path: Source file path
            dest_path: Destination file path
            verify_checksum: Whether to verify file integrity
            overwrite: Whether to overwrite existing files
            
        Returns:
            Dictionary with copy operation results

        """
        try:
            source_path_obj = Path(source_path)
            dest_path_obj = Path(dest_path)

            # Check source file exists
            if not source_path_obj.exists():
                raise FileNotFoundError(f"Source file not found: {source_path}")

            # Check destination
            if dest_path_obj.exists() and not overwrite:
                raise FileExistsError(f"Destination file exists: {dest_path}")

            # Create destination directory
            dest_path_obj.parent.mkdir(parents=True, exist_ok=True)

            # Get source hash if verification is enabled
            source_hash = None
            if verify_checksum:
                source_hash = await self.file_reader.calculate_file_hash(source_path)

            copied_bytes = 0

            # Copy file in chunks
            async with aiofiles.open(source_path, 'rb') as src:
                async with aiofiles.open(dest_path, 'wb') as dst:
                    while chunk := await src.read(self.CHUNK_SIZE):
                        await dst.write(chunk)
                        copied_bytes += len(chunk)

            # Verify integrity if requested
            if verify_checksum:
                dest_hash = await self.file_reader.calculate_file_hash(dest_path)
                if source_hash != dest_hash:
                    await aiofiles.os.remove(dest_path)
                    raise ValueError("File integrity check failed: checksum mismatch")

            # Get destination file stats
            dest_stats = await aiofiles.os.stat(dest_path)

            result = {
                "source_path": source_path,
                "dest_path": dest_path,
                "size": dest_stats.st_size,
                "copied_bytes": copied_bytes,
                "verified": verify_checksum,
                "completed_at": datetime.utcnow()
            }

            if verify_checksum:
                result["checksum"] = source_hash

            logger.info("File copied successfully", **{k: v for k, v in result.items() if k != 'checksum'})
            return result

        except Exception as e:
            # Clean up partial file
            try:
                if Path(dest_path).exists():
                    await aiofiles.os.remove(dest_path)
            except:
                pass

            logger.error("Error copying file",
                        source_path=source_path,
                        dest_path=dest_path,
                        error=str(e))
            raise

    async def move_file_async(
        self,
        source_path: str,
        dest_path: str,
        verify_checksum: bool = True
    ) -> Dict[str, Any]:
        """Move file asynchronously with integrity verification
        
        Args:
            source_path: Source file path
            dest_path: Destination file path
            verify_checksum: Whether to verify file integrity
            
        Returns:
            Dictionary with move operation results

        """
        try:
            # First copy the file
            copy_result = await self.copy_file_async(source_path, dest_path, verify_checksum, overwrite=True)

            # If copy was successful, delete source
            await self.delete_file_async(source_path)

            result = {
                **copy_result,
                "operation": "move",
                "source_deleted": True
            }

            logger.info("File moved successfully",
                       source_path=source_path,
                       dest_path=dest_path)
            return result

        except Exception as e:
            logger.error("Error moving file",
                        source_path=source_path,
                        dest_path=dest_path,
                        error=str(e))
            raise

    async def delete_file_async(self, file_path: str) -> bool:
        """Delete file asynchronously
        
        Args:
            file_path: Path to file to delete
            
        Returns:
            True if deleted successfully, False otherwise

        """
        try:
            if not Path(file_path).exists():
                logger.warning("File not found for deletion", file_path=file_path)
                return False

            await aiofiles.os.remove(file_path)
            logger.info("File deleted successfully", file_path=file_path)
            return True

        except Exception as e:
            logger.error("Error deleting file", file_path=file_path, error=str(e))
            return False

    async def compare_files(self, file1_path: str, file2_path: str) -> Dict[str, Any]:
        """Compare two files for equality
        
        Args:
            file1_path: First file path
            file2_path: Second file path
            
        Returns:
            Comparison results

        """
        try:
            # Check both files exist
            if not Path(file1_path).exists():
                raise FileNotFoundError(f"File 1 not found: {file1_path}")
            if not Path(file2_path).exists():
                raise FileNotFoundError(f"File 2 not found: {file2_path}")

            # Get file sizes
            size1 = await self.file_reader.get_file_size(file1_path)
            size2 = await self.file_reader.get_file_size(file2_path)

            # If sizes differ, files are different
            if size1 != size2:
                return {
                    "are_equal": False,
                    "reason": "different_sizes",
                    "file1_size": size1,
                    "file2_size": size2
                }

            # Compare hashes
            hash1 = await self.file_reader.calculate_file_hash(file1_path)
            hash2 = await self.file_reader.calculate_file_hash(file2_path)

            are_equal = hash1 == hash2

            result = {
                "are_equal": are_equal,
                "file1_path": file1_path,
                "file2_path": file2_path,
                "size": size1,
                "file1_hash": hash1,
                "file2_hash": hash2
            }

            if not are_equal:
                result["reason"] = "different_content"

            logger.info("File comparison completed",
                       file1=file1_path,
                       file2=file2_path,
                       are_equal=are_equal)

            return result

        except Exception as e:
            logger.error("Error comparing files",
                        file1=file1_path,
                        file2=file2_path,
                        error=str(e))
            raise

    async def batch_delete_files(self, file_paths: list[str]) -> Dict[str, Any]:
        """Delete multiple files in batch
        
        Args:
            file_paths: List of file paths to delete
            
        Returns:
            Batch deletion results

        """
        deleted_count = 0
        failed_count = 0
        failed_files = []

        for file_path in file_paths:
            try:
                success = await self.delete_file_async(file_path)
                if success:
                    deleted_count += 1
                else:
                    failed_count += 1
                    failed_files.append(file_path)
            except Exception as e:
                failed_count += 1
                failed_files.append(file_path)
                logger.error("Failed to delete file in batch", file_path=file_path, error=str(e))

        result = {
            "total_files": len(file_paths),
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "failed_files": failed_files,
            "success_rate": deleted_count / len(file_paths) if file_paths else 0
        }

        logger.info("Batch deletion completed", **result)
        return result

    async def ensure_directory_exists(self, dir_path: str) -> bool:
        """Ensure directory exists, create if necessary
        
        Args:
            dir_path: Directory path
            
        Returns:
            True if directory exists or was created

        """
        try:
            path_obj = Path(dir_path)
            path_obj.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            logger.error("Error ensuring directory exists", dir_path=dir_path, error=str(e))
            return False

    async def get_directory_size(self, dir_path: str) -> Dict[str, Any]:
        """Calculate total size of directory recursively
        
        Args:
            dir_path: Directory path
            
        Returns:
            Directory size information

        """
        try:
            path_obj = Path(dir_path)

            if not path_obj.exists():
                raise FileNotFoundError(f"Directory not found: {dir_path}")

            if not path_obj.is_dir():
                raise ValueError(f"Path is not a directory: {dir_path}")

            total_size = 0
            file_count = 0

            for file_path in path_obj.rglob("*"):
                if file_path.is_file():
                    try:
                        file_stats = await aiofiles.os.stat(file_path)
                        total_size += file_stats.st_size
                        file_count += 1
                    except Exception:
                        continue

            return {
                "directory": str(path_obj),
                "total_size": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_count": file_count,
                "avg_file_size": total_size / file_count if file_count > 0 else 0
            }

        except Exception as e:
            logger.error("Error calculating directory size", dir_path=dir_path, error=str(e))
            raise

    def get_operations_config(self) -> Dict[str, Any]:
        """Get operations configuration
        
        Returns:
            Configuration information

        """
        return {
            "chunk_size": self.CHUNK_SIZE,
            "chunk_size_kb": self.CHUNK_SIZE / 1024,
            "file_reader": type(self.file_reader).__name__
        }


# Default instance
async_file_operations = AsyncFileOperations()
