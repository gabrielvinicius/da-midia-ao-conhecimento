"""Text extraction pipeline using Chain of Responsibility Pattern
"""
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict

from src.shared.patterns.chain_of_responsibility import (
    ChainBuilder,
    ProcessingContext,
    ProcessingPipeline,
    TransformationHandler,
    ValidationHandler,
)


class TextType(str, Enum):
    """Supported text types"""

    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    HTML = "html"
    MARKDOWN = "md"


@dataclass
class TextExtractionRequest:
    """Request object for text extraction pipeline"""

    file_data: bytes
    file_type: TextType
    filename: str
    extraction_options: Dict[str, Any] = None
    quality_threshold: float = 0.8

    def __post_init__(self):
        if self.extraction_options is None:
            self.extraction_options = {}


class FileTypeDetectionHandler(ValidationHandler):
    """Detect and validate file type"""

    def __init__(self):
        super().__init__("FileTypeDetector")
        self.type_signatures = {
            TextType.PDF: [b'%PDF'],
            TextType.DOCX: [b'PK\x03\x04', b'PK\x05\x06', b'PK\x07\x08'],
            TextType.TXT: [],  # Any file can be treated as text
            TextType.HTML: [b'<!DOCTYPE', b'<html', b'<HTML'],
            TextType.MARKDOWN: []  # Extension-based detection
        }

    async def validate(self, context: ProcessingContext) -> bool:
        """Detect and validate file type"""
        request: TextExtractionRequest = context.request

        # Check file signature
        detected_type = self._detect_type(request.file_data, request.filename)

        if detected_type != request.file_type:
            context.add_metadata("detected_type", detected_type.value)
            context.add_metadata("declared_type", request.file_type.value)

            # Allow override for some types
            if self._is_override_allowed(detected_type, request.file_type):
                context.add_metadata("type_override", "allowed")
                return True
            else:
                context.add_error(
                    f"File type mismatch. Detected: {detected_type.value}, "
                    f"Declared: {request.file_type.value}"
                )
                return False

        context.add_metadata("file_type_validated", request.file_type.value)
        return True

    def _detect_type(self, file_data: bytes, filename: str) -> TextType:
        """Detect file type from content and filename"""
        # Check file signatures
        for file_type, signatures in self.type_signatures.items():
            for signature in signatures:
                if file_data.startswith(signature):
                    return file_type

        # Check file extension
        if filename.lower().endswith('.pdf'):
            return TextType.PDF
        elif filename.lower().endswith('.docx'):
            return TextType.DOCX
        elif filename.lower().endswith(('.html', '.htm')):
            return TextType.HTML
        elif filename.lower().endswith(('.md', '.markdown')):
            return TextType.MARKDOWN
        else:
            return TextType.TXT

    def _is_override_allowed(self, detected: TextType, declared: TextType) -> bool:
        """Check if type override is allowed"""
        # Allow treating any file as plain text
        if declared == TextType.TXT:
            return True
        # Allow markdown files to be treated as text
        if detected == TextType.MARKDOWN and declared == TextType.TXT:
            return True
        return False


class FileSizeValidationHandler(ValidationHandler):
    """Validate file size for text extraction"""

    def __init__(self, max_size_mb: int = 50):
        super().__init__("FileSizeValidator")
        self.max_size_bytes = max_size_mb * 1024 * 1024

    async def validate(self, context: ProcessingContext) -> bool:
        """Validate file size"""
        request: TextExtractionRequest = context.request
        file_size = len(request.file_data)

        if file_size > self.max_size_bytes:
            context.add_error(
                f"File size {file_size} bytes exceeds limit of {self.max_size_bytes} bytes"
            )
            return False

        if file_size == 0:
            context.add_error("File is empty")
            return False

        context.add_metadata("file_size", file_size)
        return True


class TextEncodingDetectionHandler(TransformationHandler):
    """Detect and handle text encoding"""

    def __init__(self):
        super().__init__("EncodingDetector")

    async def transform(self, context: ProcessingContext) -> None:
        """Detect text encoding"""
        request: TextExtractionRequest = context.request

        # For binary formats, encoding detection is not applicable
        if request.file_type in [TextType.PDF, TextType.DOCX]:
            context.add_metadata("encoding", "binary_format")
            return

        try:
            # Try common encodings
            encodings = ['utf-8', 'utf-16', 'iso-8859-1', 'cp1252']
            detected_encoding = None

            for encoding in encodings:
                try:
                    request.file_data.decode(encoding)
                    detected_encoding = encoding
                    break
                except UnicodeDecodeError:
                    continue

            if detected_encoding:
                context.add_metadata("detected_encoding", detected_encoding)
                # Store decoded text for further processing
                decoded_text = request.file_data.decode(detected_encoding)
                context.add_metadata("decoded_text", decoded_text)
            else:
                context.add_metadata("encoding_detection", "failed")
                # Fallback to utf-8 with error handling
                decoded_text = request.file_data.decode('utf-8', errors='replace')
                context.add_metadata("decoded_text", decoded_text)
                context.add_metadata("detected_encoding", "utf-8_with_errors")

        except Exception as e:
            context.add_metadata("encoding_error", str(e))


class PDFTextExtractionHandler(TransformationHandler):
    """Extract text from PDF files"""

    def __init__(self, pdf_extractor=None):
        super().__init__("PDFExtractor")
        self.pdf_extractor = pdf_extractor

    def can_handle(self, context: ProcessingContext) -> bool:
        """Only handle PDF files"""
        request: TextExtractionRequest = context.request
        return request.file_type == TextType.PDF

    async def transform(self, context: ProcessingContext) -> None:
        """Extract text from PDF"""
        if not self.can_handle(context):
            return

        request: TextExtractionRequest = context.request

        try:
            if self.pdf_extractor:
                extracted_text = await self.pdf_extractor.extract(
                    request.file_data,
                    request.extraction_options
                )
            else:
                # Fallback basic extraction
                extracted_text = "PDF extraction not available"

            context.add_metadata("extracted_text", extracted_text)
            context.add_metadata("extraction_method", "pdf_extractor")

        except Exception as e:
            context.add_metadata("extraction_error", str(e))
            context.add_metadata("extracted_text", "")


class DOCXTextExtractionHandler(TransformationHandler):
    """Extract text from DOCX files"""

    def __init__(self, docx_extractor=None):
        super().__init__("DOCXExtractor")
        self.docx_extractor = docx_extractor

    def can_handle(self, context: ProcessingContext) -> bool:
        """Only handle DOCX files"""
        request: TextExtractionRequest = context.request
        return request.file_type == TextType.DOCX

    async def transform(self, context: ProcessingContext) -> None:
        """Extract text from DOCX"""
        if not self.can_handle(context):
            return

        request: TextExtractionRequest = context.request

        try:
            if self.docx_extractor:
                extracted_text = await self.docx_extractor.extract(
                    request.file_data,
                    request.extraction_options
                )
            else:
                # Fallback basic extraction
                extracted_text = "DOCX extraction not available"

            context.add_metadata("extracted_text", extracted_text)
            context.add_metadata("extraction_method", "docx_extractor")

        except Exception as e:
            context.add_metadata("extraction_error", str(e))
            context.add_metadata("extracted_text", "")


class PlainTextExtractionHandler(TransformationHandler):
    """Handle plain text files"""

    def __init__(self):
        super().__init__("PlainTextExtractor")

    def can_handle(self, context: ProcessingContext) -> bool:
        """Handle text-based files"""
        request: TextExtractionRequest = context.request
        return request.file_type in [TextType.TXT, TextType.HTML, TextType.MARKDOWN]

    async def transform(self, context: ProcessingContext) -> None:
        """Extract text from plain text files"""
        if not self.can_handle(context):
            return

        # Text should already be decoded by encoding handler
        decoded_text = context.metadata.get("decoded_text", "")

        if not decoded_text:
            context.add_metadata("extracted_text", "")
            context.add_metadata("extraction_error", "No decoded text available")
            return

        # For HTML, we might want to strip tags
        if context.request.file_type == TextType.HTML:
            cleaned_text = self._strip_html_tags(decoded_text)
            context.add_metadata("extracted_text", cleaned_text)
            context.add_metadata("extraction_method", "html_tag_stripping")
        else:
            context.add_metadata("extracted_text", decoded_text)
            context.add_metadata("extraction_method", "plain_text")

    def _strip_html_tags(self, html_text: str) -> str:
        """Basic HTML tag stripping"""
        import re
        # Remove HTML tags
        clean = re.compile('<.*?>')
        text = re.sub(clean, '', html_text)
        # Clean up multiple whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


class TextQualityValidationHandler(ValidationHandler):
    """Validate extracted text quality"""

    def __init__(self):
        super().__init__("TextQualityValidator")

    async def validate(self, context: ProcessingContext) -> bool:
        """Validate text quality"""
        extracted_text = context.metadata.get("extracted_text", "")
        request: TextExtractionRequest = context.request

        if not extracted_text:
            context.add_error("No text was extracted")
            return False

        # Basic quality checks
        text_length = len(extracted_text.strip())
        if text_length < 10:
            context.add_error(f"Extracted text too short: {text_length} characters")
            return False

        # Check for garbled text (high ratio of non-printable characters)
        printable_chars = sum(1 for c in extracted_text if c.isprintable() or c.isspace())
        quality_ratio = printable_chars / len(extracted_text) if extracted_text else 0

        if quality_ratio < request.quality_threshold:
            context.add_error(
                f"Text quality too low: {quality_ratio:.2f} < {request.quality_threshold}"
            )
            return False

        context.add_metadata("text_length", text_length)
        context.add_metadata("quality_ratio", quality_ratio)
        context.add_metadata("quality_check", "passed")

        return True


class TextCleanupHandler(TransformationHandler):
    """Clean up extracted text"""

    def __init__(self):
        super().__init__("TextCleanup")

    async def transform(self, context: ProcessingContext) -> None:
        """Clean up extracted text"""
        extracted_text = context.metadata.get("extracted_text", "")

        if not extracted_text:
            return

        # Basic cleanup
        cleaned_text = self._clean_text(extracted_text)

        context.add_metadata("cleaned_text", cleaned_text)
        context.add_metadata("cleanup_applied", True)

        # Update the extracted_text with cleaned version
        context.metadata["extracted_text"] = cleaned_text

    def _clean_text(self, text: str) -> str:
        """Apply text cleaning rules"""
        import re

        # Remove multiple whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove excessive newlines
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text


class TextExtractionPipelineFactory:
    """Factory for creating text extraction pipelines"""

    @staticmethod
    def create_basic_pipeline() -> ProcessingPipeline:
        """Create basic text extraction pipeline"""
        chain = (ChainBuilder("TextExtractionBasic")
                .add_validation(FileSizeValidationHandler())
                .add_validation(FileTypeDetectionHandler())
                .add_transformation(TextEncodingDetectionHandler())
                .add_transformation(PlainTextExtractionHandler())
                .add_transformation(TextCleanupHandler())
                .add_validation(TextQualityValidationHandler())
                .build())

        return ProcessingPipeline("TextExtractionBasic", chain)

    @staticmethod
    def create_advanced_pipeline(
        pdf_extractor=None,
        docx_extractor=None,
        max_file_size_mb: int = 50
    ) -> ProcessingPipeline:
        """Create advanced text extraction pipeline"""
        chain = (ChainBuilder("TextExtractionAdvanced")
                .add_validation(FileSizeValidationHandler(max_file_size_mb))
                .add_validation(FileTypeDetectionHandler())
                .add_transformation(TextEncodingDetectionHandler())
                .add_transformation(PDFTextExtractionHandler(pdf_extractor))
                .add_transformation(DOCXTextExtractionHandler(docx_extractor))
                .add_transformation(PlainTextExtractionHandler())
                .add_transformation(TextCleanupHandler())
                .add_validation(TextQualityValidationHandler())
                .build())

        return ProcessingPipeline("TextExtractionAdvanced", chain)


def register_text_processing_pipelines():
    """Register text processing pipelines"""
    from src.shared.patterns.chain_of_responsibility import PipelineRegistry

    # Basic pipeline
    basic_pipeline = TextExtractionPipelineFactory.create_basic_pipeline()
    PipelineRegistry.register_pipeline("text_extraction_basic", basic_pipeline)

    # Advanced pipeline
    advanced_pipeline = TextExtractionPipelineFactory.create_advanced_pipeline()
    PipelineRegistry.register_pipeline("text_extraction_advanced", advanced_pipeline)
