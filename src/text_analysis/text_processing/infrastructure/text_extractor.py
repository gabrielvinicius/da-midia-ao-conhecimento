"""Concrete implementation of the text extraction service."""
from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Protocol

import structlog

from src.storage.infrastructure.dependencies import StorageServiceFactory

logger = structlog.get_logger(__name__)


class TextExtractor:
    """Orchestrates text extraction using the configured pipelines and storage service."""

    def __init__(
        self,
        basic_extraction_pipeline: ProcessingPipeline,
        advanced_extraction_pipeline: ProcessingPipeline,
        storage_factory: StorageServiceFactory,
        default_storage_provider: str = "local",
    ) -> None:
        self.basic_extraction_pipeline = basic_extraction_pipeline
        self.advanced_extraction_pipeline = advanced_extraction_pipeline
        self._storage_factory = storage_factory
        self._default_storage_provider = default_storage_provider

    async def extract_text(
        self,
        file_path: str,
        extraction_method: str,
        *,
        storage_provider: Optional[str] = None,
    ) -> str:
        logger.info(
            "text_extractor.extracting_text",
            file_path=file_path,
            extraction_method=extraction_method,
        )

        provider = storage_provider or self._default_storage_provider
        file_data = await self._download_file(file_path, provider)
        file_type = self._infer_file_type(file_path)
        pipeline_to_use = self._select_pipeline(extraction_method, file_type)

        request = TextExtractionRequest(
            file_data=file_data,
            file_type=file_type,
            filename=os.path.basename(file_path),
            extraction_options={"method": extraction_method},
        )

        context = await pipeline_to_use.execute(request)

        if context.is_successful():
            extracted_content = context.metadata.get("extracted_text", "")
            logger.info(
                "text_extractor.text_extracted",
                extracted_content_preview=extracted_content[:50],
            )
            return extracted_content

        logger.error(
            "text_extractor.extraction_failed",
            errors=context.errors,
        )
        raise RuntimeError(f"Text extraction failed: {context.errors}")

    def extract_text_sync(
        self,
        file_path: str,
        extraction_method: str,
        *,
        storage_provider: Optional[str] = None,
    ) -> str:
        logger.info(
            "text_extractor.extracting_text_sync",
            file_path=file_path,
            extraction_method=extraction_method,
        )

        provider = storage_provider or self._default_storage_provider
        file_data = self._download_file_sync(file_path, provider)
        file_type = self._infer_file_type(file_path)
        pipeline_to_use = self._select_pipeline(extraction_method, file_type)

        request = TextExtractionRequest(
            file_data=file_data,
            file_type=file_type,
            filename=os.path.basename(file_path),
            extraction_options={"method": extraction_method},
        )

        # Use sync execution if available, otherwise use async in a new event loop
        if hasattr(pipeline_to_use, 'execute_sync'):
            context = pipeline_to_use.execute_sync(request)
        else:
            import asyncio
            try:
                # Check if pipeline has a sync method, otherwise try async
                if hasattr(pipeline_to_use, 'execute_sync'):
                    context = pipeline_to_use.execute_sync(request)
                else:
                    import asyncio
                    try:
                        context = asyncio.run(pipeline_to_use.execute(request))
                    except RuntimeError:
                        # If there's already an event loop running, use thread-based approach
                        import concurrent.futures
                        def run_async():
                            import asyncio
                            return asyncio.run(pipeline_to_use.execute(request))
                        
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(run_async)
                            context = future.result()
            except RuntimeError:
                # If there's already an event loop, try to handle differently
                import concurrent.futures
                import threading
                
                def run_async():
                    return asyncio.run(pipeline_to_use.execute(request))
                
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_async)
                    context = future.result()

        if context.is_successful():
            extracted_content = context.metadata.get("extracted_text", "")
            logger.info(
                "text_extractor.text_extracted_sync",
                extracted_content_preview=extracted_content[:50],
            )
            return extracted_content

        logger.error(
            "text_extractor.extraction_failed_sync",
            errors=context.errors,
        )
        raise RuntimeError(f"Text extraction failed: {context.errors}")

    async def _download_file(self, file_path: str, provider: str) -> bytes:
        try:
            storage_client = self._storage_factory.get_download_service(provider)
            return await storage_client.download_file(file_path)
        except Exception as exc:
            logger.error(
                "text_extractor.download_failed",
                file_path=file_path,
                error=str(exc),
                exc_info=True,
            )
            raise

    def _download_file_sync(self, file_path: str, provider: str) -> bytes:
        try:
            # Sync version might need to handle differently depending on the storage client
            # For now, we'll try to handle this case
            storage_client = self._storage_factory.get_download_service(provider)
            if hasattr(storage_client, 'download_file_sync'):
                return storage_client.download_file_sync(file_path)
            else:
                # If no sync method, use async in a new event loop
                import asyncio
                try:
                    return asyncio.run(storage_client.download_file(file_path))
                except RuntimeError:
                    # If there's already an event loop, we need to run in a separate thread
                    import concurrent.futures
                    import threading
                    
                    def run_async():
                        return asyncio.run(storage_client.download_file(file_path))
                    
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_async)
                        return future.result()
        except Exception as exc:
            logger.error(
                "text_extractor.download_failed_sync",
                file_path=file_path,
                error=str(exc),
                exc_info=True,
            )
            raise

    @staticmethod
    def _infer_file_type(file_path: str) -> TextType:
        extension = os.path.splitext(file_path)[1].lstrip(".").upper()
        mapping = {
            "PDF": TextType.PDF,
            "DOCX": TextType.DOCX,
            "HTML": TextType.HTML,
            "HTM": TextType.HTML,
            "MD": TextType.MARKDOWN,
        }
        return mapping.get(extension, TextType.TXT)

    def _select_pipeline(self, extraction_method: str, file_type: TextType) -> ProcessingPipeline:
        if extraction_method == "advanced" or file_type in {TextType.PDF, TextType.DOCX}:
            return self.advanced_extraction_pipeline
        return self.basic_extraction_pipeline

class ProcessingPipeline(Protocol):
    """Minimal protocol describing the expected pipeline behaviour."""

    async def execute(self, request: "TextExtractionRequest") -> "PipelineContext":  # pragma: no cover - protocol
        ...


class PipelineContext:
    """Lightweight execution context used by the placeholder pipeline."""

    def __init__(self, successful: bool, metadata: Optional[Dict[str, Any]] = None, errors: Optional[list[str]] = None) -> None:
        self._successful = successful
        self.metadata: Dict[str, Any] = metadata or {}
        self.errors: list[str] = errors or []

    def is_successful(self) -> bool:
        return self._successful


class TextType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    HTML = "html"
    MARKDOWN = "md"


@dataclass(slots=True)
class TextExtractionRequest:
    file_data: bytes
    file_type: TextType
    filename: str
    extraction_options: Dict[str, Any]
