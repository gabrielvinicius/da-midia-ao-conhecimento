"""
Unified storage service - eliminating storage implementation duplication
"""
import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Union, Optional, Tuple, Dict, Any
import structlog

logger = structlog.get_logger(__name__)

class StorageException(Exception):
    """Base storage exception"""
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(message)
        self.original_error = original_error

class UnifiedStorageService(ABC):
    """Base storage service eliminating implementation duplication"""
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Provider identifier"""
        pass
    
    @abstractmethod
    async def upload(self, file_path: Union[str, Path], file: bytes) -> bool:
        """Upload file"""
        pass
    
    @abstractmethod
    async def download(self, file_path: Union[str, Path]) -> Optional[Tuple[bytes, str]]:
        """Download file - returns (content, filename)"""
        pass
    
    @abstractmethod
    async def delete(self, file_path: Union[str, Path]) -> bool:
        """Delete file"""
        pass
    
    @abstractmethod
    async def exists(self, file_path: Union[str, Path]) -> bool:
        """Check if file exists"""
        pass
    
    # Common helper methods
    async def upload_with_retry(self, file_path: Union[str, Path], file: bytes, max_retries: int = 3) -> bool:
        """Upload with retry logic"""
        for attempt in range(max_retries):
            try:
                return await self.upload(file_path, file)
            except StorageException as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Upload attempt {attempt + 1} failed, retrying...", error=str(e))
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        return False
    
    def get_file_info(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """Get file information"""
        path_obj = Path(file_path)
        return {
            "name": path_obj.name,
            "stem": path_obj.stem,
            "suffix": path_obj.suffix,
            "parent": str(path_obj.parent),
            "provider": self.provider_name
        }

class LocalStorage(UnifiedStorageService):
    """Local filesystem storage implementation"""
    
    def __init__(self, root_path: str = "storage"):
        self.root = Path(root_path)
        self.root.mkdir(exist_ok=True, parents=True)
    
    @property
    def provider_name(self) -> str:
        return "local"
    
    async def upload(self, file_path: Union[str, Path], file: bytes) -> bool:
        path = self.root / file_path
        try:
            await asyncio.to_thread(self._sync_upload, path, file)
            return True
        except Exception as e:
            raise StorageException("Error saving file locally", e)
    
    def _sync_upload(self, path: Path, file: bytes):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(file)
    
    async def download(self, file_path: Union[str, Path]) -> Optional[Tuple[bytes, str]]:
        path = self.root / file_path
        try:
            content = await asyncio.to_thread(path.read_bytes)
            return content, path.name
        except FileNotFoundError:
            return None
        except Exception as e:
            raise StorageException("Error reading file locally", e)
    
    async def delete(self, file_path: Union[str, Path]) -> bool:
        path = self.root / file_path
        try:
            return await asyncio.to_thread(self._sync_delete, path)
        except Exception as e:
            raise StorageException("Error deleting file locally", e)
    
    def _sync_delete(self, path: Path) -> bool:
        if path.exists():
            path.unlink()
            return True
        return False
    
    async def exists(self, file_path: Union[str, Path]) -> bool:
        path = self.root / file_path
        return await asyncio.to_thread(path.exists)

class S3Storage(UnifiedStorageService):
    """S3-compatible storage implementation"""
    
    def __init__(self, bucket_name: str, access_key: str, secret_key: str, endpoint_url: str = None):
        import boto3
        from botocore.exceptions import ClientError
        
        self.bucket_name = bucket_name
        self.client = boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint_url,
        )
        
        # Ensure bucket exists
        try:
            self.client.head_bucket(Bucket=bucket_name)
        except ClientError:
            self.client.create_bucket(Bucket=bucket_name)
    
    @property
    def provider_name(self) -> str:
        return "s3"
    
    async def upload(self, file_path: Union[str, Path], file: bytes) -> bool:
        try:
            await asyncio.to_thread(
                self.client.put_object,
                Bucket=self.bucket_name,
                Key=str(file_path),
                Body=file
            )
            return True
        except Exception as e:
            raise StorageException("Error uploading to S3", e)
    
    async def download(self, file_path: Union[str, Path]) -> Optional[Tuple[bytes, str]]:
        try:
            response = await asyncio.to_thread(
                self.client.get_object,
                Bucket=self.bucket_name,
                Key=str(file_path)
            )
            content = response["Body"].read()
            filename = str(file_path).split('/')[-1]
            return content, filename
        except self.client.exceptions.NoSuchKey:
            return None
        except Exception as e:
            raise StorageException("Error downloading from S3", e)
    
    async def delete(self, file_path: Union[str, Path]) -> bool:
        try:
            await asyncio.to_thread(
                self.client.delete_object,
                Bucket=self.bucket_name,
                Key=str(file_path)
            )
            return True
        except Exception as e:
            raise StorageException("Error deleting from S3", e)
    
    async def exists(self, file_path: Union[str, Path]) -> bool:
        try:
            await asyncio.to_thread(
                self.client.head_object,
                Bucket=self.bucket_name,
                Key=str(file_path)
            )
            return True
        except Exception:
            return False

# Storage factory
class StorageFactory:
    """Simple storage factory"""
    
    @staticmethod
    def create_storage(provider: str, **config) -> UnifiedStorageService:
        """Create storage instance"""
        if provider == "local":
            return LocalStorage(config.get("root_path", "storage"))
        elif provider == "s3":
            return S3Storage(
                bucket_name=config["bucket_name"],
                access_key=config["access_key"], 
                secret_key=config["secret_key"],
                endpoint_url=config.get("endpoint_url")
            )
        else:
            raise ValueError(f"Unknown storage provider: {provider}")