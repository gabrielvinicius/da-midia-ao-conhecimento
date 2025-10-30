"""
Media upload pipeline using Chain of Responsibility Pattern
"""
from typing import Dict, Any
from uuid import UUID
import mimetypes
from dataclasses import dataclass

from src.shared.patterns.chain_of_responsibility import (
    ValidationHandler, TransformationHandler, FilterHandler,
    ProcessingContext, HandlerResult, ChainBuilder, ProcessingPipeline
)


@dataclass
class MediaUploadRequest:
    """Request object for media upload pipeline"""
    user_id: UUID
    file_data: bytes
    filename: str
    content_type: str = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.content_type is None:
            self.content_type = mimetypes.guess_type(self.filename)[0] or "application/octet-stream"


class FileSizeValidationHandler(ValidationHandler):
    """Validate file size limits"""
    
    def __init__(self, max_size_mb: int = 100):
        super().__init__("FileSizeValidator")
        self.max_size_bytes = max_size_mb * 1024 * 1024
    
    async def validate(self, context: ProcessingContext) -> bool:
        """Validate file size"""
        request: MediaUploadRequest = context.request
        file_size = len(request.file_data)
        
        if file_size > self.max_size_bytes:
            context.add_error(
                f"File size {file_size} bytes exceeds limit of {self.max_size_bytes} bytes"
            )
            return False
        
        context.add_metadata("file_size", file_size)
        return True


class FileTypeValidationHandler(ValidationHandler):
    """Validate allowed file types"""
    
    def __init__(self, allowed_types: list = None):
        super().__init__("FileTypeValidator")
        self.allowed_types = allowed_types or [
            "image/jpeg", "image/png", "image/gif",
            "video/mp4", "video/avi", "video/mov",
            "audio/mp3", "audio/wav", "audio/m4a",
            "application/pdf", "text/plain"
        ]
    
    async def validate(self, context: ProcessingContext) -> bool:
        """Validate file type"""
        request: MediaUploadRequest = context.request
        
        if request.content_type not in self.allowed_types:
            context.add_error(
                f"File type {request.content_type} not allowed. "
                f"Allowed types: {', '.join(self.allowed_types)}"
            )
            return False
        
        context.add_metadata("content_type", request.content_type)
        return True


class FilenameValidationHandler(ValidationHandler):
    """Validate filename format and security"""
    
    def __init__(self):
        super().__init__("FilenameValidator")
        self.forbidden_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        self.max_length = 255
    
    async def validate(self, context: ProcessingContext) -> bool:
        """Validate filename"""
        request: MediaUploadRequest = context.request
        filename = request.filename
        
        # Check length
        if len(filename) > self.max_length:
            context.add_error(f"Filename too long (max {self.max_length} characters)")
            return False
        
        # Check for forbidden characters
        for char in self.forbidden_chars:
            if char in filename:
                context.add_error(f"Filename contains forbidden character: {char}")
                return False
        
        # Check for dangerous patterns
        dangerous_patterns = ['../', '..\\', 'CON', 'PRN', 'AUX', 'NUL']
        filename_upper = filename.upper()
        for pattern in dangerous_patterns:
            if pattern in filename_upper:
                context.add_error(f"Filename contains dangerous pattern: {pattern}")
                return False
        
        context.add_metadata("validated_filename", filename)
        return True


class UserQuotaValidationHandler(ValidationHandler):
    """Validate user storage quota"""
    
    def __init__(self, quota_service):
        super().__init__("UserQuotaValidator")
        self.quota_service = quota_service
    
    async def validate(self, context: ProcessingContext) -> bool:
        """Validate user quota"""
        request: MediaUploadRequest = context.request
        file_size = len(request.file_data)
        
        try:
            # Check user's current usage and quota
            current_usage = await self.quota_service.get_user_usage(request.user_id)
            quota_limit = await self.quota_service.get_user_quota(request.user_id)
            
            if current_usage + file_size > quota_limit:
                context.add_error(
                    f"Upload would exceed quota. "
                    f"Current: {current_usage}, Limit: {quota_limit}, "
                    f"File size: {file_size}"
                )
                return False
            
            context.add_metadata("quota_check", {
                "current_usage": current_usage,
                "quota_limit": quota_limit,
                "after_upload": current_usage + file_size
            })
            return True
            
        except Exception as e:
            context.add_error(f"Quota validation failed: {str(e)}")
            return False


class VirusScanHandler(ValidationHandler):
    """Scan file for malware"""
    
    def __init__(self, virus_scanner=None):
        super().__init__("VirusScanner")
        self.virus_scanner = virus_scanner
    
    async def validate(self, context: ProcessingContext) -> bool:
        """Scan for viruses"""
        if not self.virus_scanner:
            # If no scanner available, log warning and continue
            context.add_metadata("virus_scan", "skipped - no scanner available")
            return True
        
        request: MediaUploadRequest = context.request
        
        try:
            is_clean = await self.virus_scanner.scan(request.file_data)
            if not is_clean:
                context.add_error("File failed virus scan")
                return False
            
            context.add_metadata("virus_scan", "clean")
            return True
            
        except Exception as e:
            context.add_error(f"Virus scan failed: {str(e)}")
            return False


class MediaMetadataExtractionHandler(TransformationHandler):
    """Extract metadata from media files"""
    
    def __init__(self, metadata_extractor=None):
        super().__init__("MetadataExtractor")
        self.metadata_extractor = metadata_extractor
    
    async def transform(self, context: ProcessingContext) -> None:
        """Extract media metadata"""
        request: MediaUploadRequest = context.request
        
        try:
            if self.metadata_extractor:
                extracted_metadata = await self.metadata_extractor.extract(
                    request.file_data, 
                    request.content_type
                )
                context.add_metadata("extracted_metadata", extracted_metadata)
            else:
                # Basic metadata extraction
                basic_metadata = {
                    "file_size": len(request.file_data),
                    "content_type": request.content_type,
                    "filename": request.filename
                }
                context.add_metadata("extracted_metadata", basic_metadata)
                
        except Exception as e:
            # Metadata extraction failure shouldn't stop upload
            context.add_metadata("metadata_extraction_error", str(e))


class ThumbnailGenerationHandler(TransformationHandler):
    """Generate thumbnails for supported media types"""
    
    def __init__(self, thumbnail_generator=None):
        super().__init__("ThumbnailGenerator")
        self.thumbnail_generator = thumbnail_generator
        self.supported_types = ["image/jpeg", "image/png", "video/mp4"]
    
    async def transform(self, context: ProcessingContext) -> None:
        """Generate thumbnail if applicable"""
        request: MediaUploadRequest = context.request
        
        if request.content_type not in self.supported_types:
            context.add_metadata("thumbnail", "not_applicable")
            return
        
        try:
            if self.thumbnail_generator:
                thumbnail_data = await self.thumbnail_generator.generate(
                    request.file_data,
                    request.content_type
                )
                context.add_metadata("thumbnail", {
                    "data": thumbnail_data,
                    "generated": True
                })
            else:
                context.add_metadata("thumbnail", "generator_not_available")
                
        except Exception as e:
            # Thumbnail generation failure shouldn't stop upload
            context.add_metadata("thumbnail_error", str(e))


class DuplicateDetectionHandler(FilterHandler):
    """Detect duplicate files"""
    
    def __init__(self, duplicate_detector=None):
        super().__init__("DuplicateDetector")
        self.duplicate_detector = duplicate_detector
    
    async def should_continue(self, context: ProcessingContext) -> bool:
        """Check for duplicates"""
        if not self.duplicate_detector:
            context.add_metadata("duplicate_check", "skipped")
            return True
        
        request: MediaUploadRequest = context.request
        
        try:
            duplicate_info = await self.duplicate_detector.check_duplicate(
                request.user_id,
                request.file_data,
                request.filename
            )
            
            if duplicate_info["is_duplicate"]:
                context.add_metadata("duplicate_check", duplicate_info)
                context.add_error(
                    f"Duplicate file detected. Original: {duplicate_info['original_id']}"
                )
                return False
            
            context.add_metadata("duplicate_check", "no_duplicates")
            return True
            
        except Exception as e:
            # Duplicate detection failure shouldn't stop upload
            context.add_metadata("duplicate_check_error", str(e))
            return True


class MediaUploadPipelineFactory:
    """Factory for creating media upload pipelines"""
    
    @staticmethod
    def create_basic_pipeline(
        max_file_size_mb: int = 100,
        allowed_types: list = None
    ) -> ProcessingPipeline:
        """Create basic upload pipeline"""
        
        chain = (ChainBuilder("MediaUploadBasic")
                .add_validation(FileSizeValidationHandler(max_file_size_mb))
                .add_validation(FileTypeValidationHandler(allowed_types))
                .add_validation(FilenameValidationHandler())
                .add_transformation(MediaMetadataExtractionHandler())
                .build())
        
        return ProcessingPipeline("MediaUploadBasic", chain)
    
    @staticmethod
    def create_enterprise_pipeline(
        max_file_size_mb: int = 100,
        allowed_types: list = None,
        quota_service=None,
        virus_scanner=None,
        metadata_extractor=None,
        thumbnail_generator=None,
        duplicate_detector=None
    ) -> ProcessingPipeline:
        """Create enterprise-grade upload pipeline"""
        
        builder = ChainBuilder("MediaUploadEnterprise")
        
        # Validation phase
        builder.add_validation(FileSizeValidationHandler(max_file_size_mb))
        builder.add_validation(FileTypeValidationHandler(allowed_types))
        builder.add_validation(FilenameValidationHandler())
        
        # Security validations
        if virus_scanner:
            builder.add_validation(VirusScanHandler(virus_scanner))
        
        if quota_service:
            builder.add_validation(UserQuotaValidationHandler(quota_service))
        
        # Duplicate detection
        if duplicate_detector:
            builder.add_filter(DuplicateDetectionHandler(duplicate_detector))
        
        # Transformation phase
        builder.add_transformation(MediaMetadataExtractionHandler(metadata_extractor))
        
        # Conditional thumbnail generation for images/videos
        if thumbnail_generator:
            builder.add_transformation(ThumbnailGenerationHandler(thumbnail_generator))
        
        chain = builder.build()
        return ProcessingPipeline("MediaUploadEnterprise", chain)


# Example usage and registration
def register_media_pipelines():
    """Register media pipelines in the global registry"""
    from src.shared.patterns.chain_of_responsibility import PipelineRegistry
    
    # Basic pipeline
    basic_pipeline = MediaUploadPipelineFactory.create_basic_pipeline()
    PipelineRegistry.register_pipeline("media_upload_basic", basic_pipeline)
    
    # Enterprise pipeline (would be configured with actual services)
    enterprise_pipeline = MediaUploadPipelineFactory.create_enterprise_pipeline()
    PipelineRegistry.register_pipeline("media_upload_enterprise", enterprise_pipeline)
