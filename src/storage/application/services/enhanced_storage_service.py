"""
Enhanced Storage Service - Single Responsibility: Orchestrate storage operations.
Follows SOLID principles by coordinating specialized storage services.
"""
import time
from typing import Dict, Any, Optional, Union, Tuple
from pathlib import Path
from uuid import UUID, uuid4
import structlog

from src.storage.application.storage_service import StorageService
from src.storage.domain.interfaces import (
    IEnhancedStorageService,
    IStorageValidator,
    IStorageMetricsService,
    IStorageStateManager
)

logger = structlog.get_logger(__name__)


class EnhancedStorageService(IEnhancedStorageService):
    """
    Enhanced storage service following SOLID principles.
    
    Single Responsibility: Orchestrate storage workflow with validation and monitoring.
    Open/Closed: Extensible through service injection.
    Liskov Substitution: Implements IEnhancedStorageService contract.
    Interface Segregation: Uses specific interfaces for each concern.
    Dependency Inversion: Depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        storage_service: StorageService,
        validator: IStorageValidator,
        metrics_service: IStorageMetricsService,
        state_manager: IStorageStateManager
    ):
        self._storage_service = storage_service
        self._validator = validator
        self._metrics_service = metrics_service
        self._state_manager = state_manager
    
    async def upload_with_validation(
        self,
        file_path: Union[str, Path], 
        file_content: bytes,
        file_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Upload file with comprehensive validation and monitoring.
        
        Args:
            file_path: Path where file will be stored
            file_content: File content bytes
            file_id: Optional file ID for tracking
            metadata: Optional file metadata
            
        Returns:
            bool: True if upload successful
        """
        if file_id is None:
            file_id = uuid4()
        
        provider = self._storage_service.provider_name
        
        try:
            # Update state to uploading
            await self._state_manager.update_file_status(file_id, "uploading")
            
            # Validate file path and content
            self._validator.validate_file_path(file_path)
            self._validator.validate_file_content(file_content, str(file_path))
            self._validator.validate_storage_operation("upload", provider)
            
            # Record upload start
            self._metrics_service.record_upload_start(file_id, len(file_content), provider)
            
            # Perform upload
            start_time = time.time()
            success = await self._storage_service.upload(file_path, file_content)
            duration = time.time() - start_time
            
            if success:
                # Record success metrics
                self._metrics_service.record_upload_success(file_id, duration, provider)
                await self._state_manager.update_file_status(file_id, "completed")
                
                logger.info(
                    "storage.upload.success",
                    file_id=str(file_id),
                    file_path=str(file_path),
                    file_size=len(file_content),
                    provider=provider,
                    duration=duration
                )
            else:
                # Record failure
                error_msg = "Upload operation returned False"
                self._metrics_service.record_upload_failure(file_id, error_msg, provider)
                await self._state_manager.update_file_status(file_id, "failed", error_msg)
                
                logger.error(
                    "storage.upload.failed",
                    file_id=str(file_id),
                    file_path=str(file_path),
                    error=error_msg
                )
            
            return success
            
        except Exception as e:
            # Record failure metrics and state
            self._metrics_service.record_upload_failure(file_id, str(e), provider)
            await self._state_manager.update_file_status(file_id, "failed", str(e))
            
            logger.error(
                "storage.upload.exception",
                file_id=str(file_id),
                file_path=str(file_path),
                error=str(e),
                provider=provider
            )
            raise
    
    async def download_with_tracking(
        self,
        file_path: Union[str, Path],
        file_id: Optional[UUID] = None
    ) -> Optional[Tuple[bytes, str]]:
        """
        Download file with tracking and monitoring.
        
        Args:
            file_path: Path of file to download
            file_id: Optional file ID for tracking
            
        Returns:
            Optional[Tuple[bytes, str]]: File content and filename, or None if not found
        """
        if file_id is None:
            file_id = uuid4()
        
        provider = self._storage_service.provider_name
        
        try:
            # Validate file path
            self._validator.validate_file_path(file_path)
            self._validator.validate_storage_operation("download", provider)
            
            # Perform download
            start_time = time.time()
            result = await self._storage_service.download(file_path)
            duration = time.time() - start_time
            
            if result:
                # Record success metrics
                self._metrics_service.record_download_success(file_id, duration, provider)
                
                logger.info(
                    "storage.download.success",
                    file_id=str(file_id),
                    file_path=str(file_path),
                    file_size=len(result[0]),
                    provider=provider,
                    duration=duration
                )
            else:
                logger.info(
                    "storage.download.not_found",
                    file_id=str(file_id),
                    file_path=str(file_path),
                    provider=provider
                )
            
            return result
            
        except Exception as e:
            logger.error(
                "storage.download.exception",
                file_id=str(file_id),
                file_path=str(file_path),
                error=str(e),
                provider=provider
            )
            raise
    
    async def delete_with_cleanup(
        self,
        file_path: Union[str, Path],
        file_id: Optional[UUID] = None
    ) -> bool:
        """
        Delete file with metadata cleanup.
        
        Args:
            file_path: Path of file to delete
            file_id: Optional file ID for tracking
            
        Returns:
            bool: True if deletion successful
        """
        if file_id is None:
            file_id = uuid4()
        
        provider = self._storage_service.provider_name
        
        try:
            # Validate operation
            self._validator.validate_file_path(file_path)
            self._validator.validate_storage_operation("delete", provider)
            
            # Update state
            await self._state_manager.update_file_status(file_id, "deleting")
            
            # Perform deletion
            success = await self._storage_service.delete(file_path)
            
            if success:
                await self._state_manager.update_file_status(file_id, "deleted")
                
                logger.info(
                    "storage.delete.success",
                    file_id=str(file_id),
                    file_path=str(file_path),
                    provider=provider
                )
            else:
                await self._state_manager.update_file_status(file_id, "failed", "Delete operation returned False")
                
                logger.warning(
                    "storage.delete.failed",
                    file_id=str(file_id),
                    file_path=str(file_path),
                    provider=provider
                )
            
            return success
            
        except Exception as e:
            await self._state_manager.update_file_status(file_id, "failed", str(e))
            
            logger.error(
                "storage.delete.exception",
                file_id=str(file_id),
                file_path=str(file_path),
                error=str(e),
                provider=provider
            )
            raise
    
    async def batch_upload(
        self,
        files: Dict[str, bytes],
        provider: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Upload multiple files in batch.
        
        Args:
            files: Dictionary mapping file paths to file content
            provider: Optional specific provider (uses current if None)
            
        Returns:
            Dict mapping file paths to success status
        """
        results = {}
        successful_count = 0
        failed_count = 0
        
        total_files = len(files)
        logger.info(
            "storage.batch_upload.started",
            total_files=total_files,
            provider=self._storage_service.provider_name
        )
        
        for file_path, file_content in files.items():
            try:
                file_id = uuid4()
                success = await self.upload_with_validation(file_path, file_content, file_id)
                results[file_path] = success
                
                if success:
                    successful_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                results[file_path] = False
                failed_count += 1
                
                logger.warning(
                    "storage.batch_upload.item_failed",
                    file_path=file_path,
                    error=str(e)
                )
        
        logger.info(
            "storage.batch_upload.completed",
            total_files=total_files,
            successful=successful_count,
            failed=failed_count,
            success_rate=round((successful_count / total_files) * 100, 2) if total_files > 0 else 0
        )
        
        return results
    
    async def check_file_exists_with_validation(self, file_path: Union[str, Path]) -> bool:
        """
        Check if file exists with path validation.
        
        Args:
            file_path: Path to check
            
        Returns:
            bool: True if file exists
        """
        try:
            # Validate file path
            self._validator.validate_file_path(file_path)
            self._validator.validate_storage_operation("exists", self._storage_service.provider_name)
            
            # Check existence
            exists = await self._storage_service.exists(file_path)
            
            logger.debug(
                "storage.exists.checked",
                file_path=str(file_path),
                exists=exists,
                provider=self._storage_service.provider_name
            )
            
            return exists
            
        except Exception as e:
            logger.error(
                "storage.exists.exception",
                file_path=str(file_path),
                error=str(e),
                provider=self._storage_service.provider_name
            )
            raise