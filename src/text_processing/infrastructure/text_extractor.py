"""
Concrete implementation of ITextExtractor for text extraction operations.
"""
import structlog
import os # Adicionar import para manipulação de arquivos
from typing import Dict, Any

from src.text_processing.domain.interfaces import ITextExtractor
from src.text_processing.infrastructure.pipelines.extraction_pipeline import (
    TextExtractionPipelineFactory,
    TextExtractionRequest,
    TextType,
    ProcessingPipeline
)
from src.shared.infrastructure.storage.s3_storage_service import S3StorageService # Assumindo que o S3 é o serviço de armazenamento

logger = structlog.get_logger(__name__)


class TextExtractor(ITextExtractor):
    """Concrete implementation for text extraction using a pipeline."""

    def __init__(self, basic_extraction_pipeline: ProcessingPipeline, advanced_extraction_pipeline: ProcessingPipeline, s3_storage_service: S3StorageService):
        self.basic_extraction_pipeline = basic_extraction_pipeline
        self.advanced_extraction_pipeline = advanced_extraction_pipeline
        self.s3_storage_service = s3_storage_service

    async def extract_text(self, file_path: str, extraction_method: str) -> str:
        logger.info(
            "text_extractor.extracting_text",
            file_path=file_path,
            extraction_method=extraction_method
        )

        # 1. Obter os dados do arquivo (assumindo que file_path é um caminho no S3)
        try:
            file_data = await self.s3_storage_service.download_file(file_path)
        except Exception as e:
            logger.error(f"Failed to download file {file_path} for extraction: {e}", exc_info=True)
            raise

        # 2. Determinar o tipo de arquivo e o pipeline a ser usado
        file_extension = os.path.splitext(file_path)[1].lstrip('.').upper()
        file_type = TextType.TXT # Default
        if file_extension == "PDF":
            file_type = TextType.PDF
        elif file_extension == "DOCX":
            file_type = TextType.DOCX
        elif file_extension == "HTML":
            file_type = TextType.HTML
        elif file_extension == "MD":
            file_type = TextType.MARKDOWN

        pipeline_to_use = self.basic_extraction_pipeline
        if extraction_method == "advanced" or file_type in [TextType.PDF, TextType.DOCX]:
            pipeline_to_use = self.advanced_extraction_pipeline

        # 3. Criar o request para o pipeline
        request = TextExtractionRequest(
            file_data=file_data,
            file_type=file_type,
            filename=os.path.basename(file_path),
            extraction_options={"method": extraction_method}
        )

        # 4. Executar o pipeline
        context = await pipeline_to_use.execute(request)

        if context.is_successful():
            extracted_content = context.metadata.get("extracted_text", "")
            logger.info("text_extractor.text_extracted", extracted_content_preview=extracted_content[:50])
            return extracted_content
        else:
            error_message = f"Text extraction failed: {context.errors}"
            logger.error("text_extractor.extraction_failed", errors=context.errors)
            raise Exception(error_message)