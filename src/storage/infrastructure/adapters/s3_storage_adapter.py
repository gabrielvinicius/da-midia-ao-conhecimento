"""Armazenamento em serviço compatível com S3 (AWS S3, MinIO).

Cada arquivo é um objeto no bucket configurado, com o caminho como chave.
O boto3 é síncrono; as chamadas rodam em outra thread para não travar o
laço de eventos.
"""
from __future__ import annotations

import asyncio
import mimetypes
from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import uuid4

from src.storage.application.ports import StorageRepositoryPort
from src.storage.domain.entities.file_metadata import FileMetadata
from src.storage.domain.value_objects.file_path import FilePath
from src.storage.domain.value_objects.file_size import FileSize


class S3StorageRepository(StorageRepositoryPort):
    def __init__(
        self,
        bucket: str,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: str = "us-east-1",
        client: Any = None,
    ) -> None:
        if client is None:
            import boto3

            client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region,
            )
        self._s3 = client
        self._bucket = bucket
        self._bucket_ready = False

    @property
    def provider_name(self) -> str:
        return "s3"

    async def store(self, file_path: FilePath, content: bytes) -> FileMetadata:
        await self._ensure_bucket()
        key = _key(file_path)
        content_type = mimetypes.guess_type(key)[0] or "application/octet-stream"
        await asyncio.to_thread(
            self._s3.put_object, Bucket=self._bucket, Key=key, Body=content, ContentType=content_type
        )
        now = datetime.now(timezone.utc)
        return FileMetadata(
            id=uuid4(),
            file_path=file_path,
            size=FileSize(len(content)),
            content_type=content_type,
            created_at=now,
            updated_at=now,
        )

    async def retrieve(self, file_path: FilePath) -> Optional[bytes]:
        try:
            response = await asyncio.to_thread(
                self._s3.get_object, Bucket=self._bucket, Key=_key(file_path)
            )
        except Exception as exc:
            if _not_found(exc):
                return None
            raise
        return await asyncio.to_thread(response["Body"].read)

    async def remove(self, file_path: FilePath) -> bool:
        if not await self.exists(file_path):
            return False
        await asyncio.to_thread(self._s3.delete_object, Bucket=self._bucket, Key=_key(file_path))
        return True

    async def remove_folder(self, folder_path: str) -> bool:
        """Remove todos os objetos sob o prefixo. False se não houver nenhum."""
        prefix = folder_path.strip("/")
        if not prefix or ".." in prefix.split("/"):
            raise ValueError(f"Pasta fora do armazenamento: {folder_path}")
        keys = await self.list_files(prefix + "/")
        for start in range(0, len(keys), 1000):  # limite do delete_objects
            batch = [{"Key": key} for key in keys[start : start + 1000]]
            await asyncio.to_thread(
                self._s3.delete_objects, Bucket=self._bucket, Delete={"Objects": batch}
            )
        return bool(keys)

    async def exists(self, file_path: FilePath) -> bool:
        return await self._head(file_path) is not None

    async def get_metadata(self, file_path: FilePath) -> Optional[FileMetadata]:
        head = await self._head(file_path)
        if head is None:
            return None
        modified = head.get("LastModified") or datetime.now(timezone.utc)
        return FileMetadata(
            id=uuid4(),
            file_path=file_path,
            size=FileSize(int(head.get("ContentLength", 0))),
            content_type=head.get("ContentType") or "application/octet-stream",
            created_at=modified,
            updated_at=modified,
        )

    async def list_files(self, prefix: str = "") -> List[str]:
        def _gather() -> List[str]:
            keys: List[str] = []
            paginator = self._s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
                keys.extend(item["Key"] for item in page.get("Contents", []))
            return keys

        await self._ensure_bucket()
        return await asyncio.to_thread(_gather)

    async def _head(self, file_path: FilePath) -> Optional[dict]:
        try:
            return await asyncio.to_thread(
                self._s3.head_object, Bucket=self._bucket, Key=_key(file_path)
            )
        except Exception as exc:
            if _not_found(exc):
                return None
            raise

    async def _ensure_bucket(self) -> None:
        """Cria o bucket na primeira gravação, se ele ainda não existir."""
        if self._bucket_ready:
            return
        try:
            await asyncio.to_thread(self._s3.head_bucket, Bucket=self._bucket)
        except Exception as exc:
            if not _not_found(exc):
                raise
            await asyncio.to_thread(self._s3.create_bucket, Bucket=self._bucket)
        self._bucket_ready = True


def _key(file_path: FilePath) -> str:
    return str(file_path).lstrip("/")


def _not_found(exc: Exception) -> bool:
    code = str(getattr(exc, "response", {}).get("Error", {}).get("Code", ""))
    return code in {"404", "NoSuchKey", "NoSuchBucket", "NotFound"}


__all__ = ["S3StorageRepository"]
