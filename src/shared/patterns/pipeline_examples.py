"""
Practical examples of Chain of Responsibility Pattern usage
"""
from uuid import UUID
from typing import Dict, Any

# Import pipeline decorators
from src.shared.patterns.pipeline_integration import (
    media_upload_pipeline, text_extraction_pipeline, auth_pipeline
)

# Import traditional decorators
from src.shared.decorators.decorator_factory import read_operation, write_operation, processing_operation


class EnhancedMediaUploadService:
    """Example service with Chain of Responsibility + Decorator Pattern"""
    
    @media_upload_pipeline("media_upload_enterprise")
    @write_operation("media_management", "upload_with_pipeline")
    async def upload_with_validation(
        self,
        user_id: UUID,
        file_data: bytes,
        filename: str,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Upload media with comprehensive pipeline validation.
        
        Pipeline will handle:
        - File size validation
        - File type validation  
        - Filename security validation
        - User quota validation
        - Virus scanning
        - Duplicate detection
        - Metadata extraction
        - Thumbnail generation
        
        Decorator will handle:
        - Input/output validation
        - Performance metrics
        - Error logging
        - Retry logic
        """
        # Business logic - simplified because pipeline handles validation
        file_path = f"uploads/{user_id}/{filename}"
        
        return {
            "file_path": file_path,
            "user_id": str(user_id),
            "filename": filename,
            "status": "uploaded",
            "metadata": metadata or {}
        }
    
    @read_operation("media_management", "get_upload_status")
    async def get_upload_status(self, upload_id: UUID) -> Dict[str, Any]:
        """Get upload status with caching and metrics"""
        # Simulated lookup
        return {
            "upload_id": str(upload_id),
            "status": "completed",
            "progress": 100
        }


class EnhancedTextExtractionService:
    """Example service with text processing pipeline"""
    
    @text_extraction_pipeline("text_extraction_advanced")
    @processing_operation("text_processing", "extract_with_pipeline")
    async def extract_text_with_pipeline(
        self,
        file_data: bytes,
        file_type: str,
        filename: str,
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Extract text with comprehensive pipeline processing.
        
        Pipeline will handle:
        - File type detection and validation
        - File size validation
        - Encoding detection
        - Type-specific extraction (PDF, DOCX, etc.)
        - Text quality validation
        - Text cleanup
        
        Decorator will handle:
        - Performance monitoring
        - Error handling
        - Retry logic
        - Metrics collection
        """
        # Business logic is minimal - pipeline does the heavy lifting
        return {
            "filename": filename,
            "file_type": file_type,
            "extraction_completed": True
        }


class EnhancedAuthenticationService:
    """Example service with authentication pipeline"""
    
    @auth_pipeline("login")
    @write_operation("auth", "login_with_pipeline")
    async def login_with_pipeline(
        self,
        username: str,
        password: str,
        client_ip: str = None,
        user_agent: str = None
    ) -> Dict[str, Any]:
        """
        Authenticate user with comprehensive pipeline validation.
        
        Pipeline will handle:
        - Rate limiting
        - Input validation
        - Security checks
        - User lookup
        - Password verification
        - Token generation
        - Audit logging
        
        Decorator will handle:
        - Request logging
        - Performance metrics
        - Error tracking
        """
        # Business logic is minimal - pipeline handles authentication
        return {
            "username": username,
            "login_completed": True
        }
    
    @auth_pipeline("access_resource")
    @read_operation("auth", "check_access_with_pipeline")
    async def check_access_with_pipeline(
        self,
        user_id: UUID,
        resource: str,
        permissions: list = None
    ) -> Dict[str, Any]:
        """
        Check resource access with authorization pipeline.
        
        Pipeline will handle:
        - User lookup
        - Permission validation
        - Audit logging
        
        Decorator will handle:
        - Caching of permission results
        - Performance metrics
        """
        return {
            "user_id": str(user_id),
            "resource": resource,
            "access_check_completed": True
        }


class PipelineMonitoringService:
    """Service for monitoring pipeline performance"""
    
    @read_operation("monitoring", "get_pipeline_metrics")
    async def get_pipeline_metrics(self, pipeline_name: str = None) -> Dict[str, Any]:
        """Get pipeline performance metrics"""
        from src.shared.patterns.chain_of_responsibility import PipelineRegistry
        
        if pipeline_name:
            pipeline = PipelineRegistry.get_pipeline(pipeline_name)
            if pipeline:
                return {
                    "pipeline": pipeline_name,
                    "metrics": pipeline.get_metrics()
                }
            else:
                return {"error": f"Pipeline {pipeline_name} not found"}
        else:
            # Get all pipeline metrics
            return PipelineRegistry.get_metrics_summary()
    
    @write_operation("monitoring", "reset_pipeline_metrics")
    async def reset_pipeline_metrics(self, pipeline_name: str) -> Dict[str, Any]:
        """Reset metrics for a specific pipeline"""
        pipeline = PipelineRegistry.get_pipeline(pipeline_name)
        if pipeline:
            pipeline._metrics = {
                "total_processed": 0,
                "successful": 0,
                "failed": 0,
                "aborted": 0
            }
            return {"status": "metrics_reset", "pipeline": pipeline_name}
        else:
            return {"error": f"Pipeline {pipeline_name} not found"}


# Utility function to register all pipelines
async def initialize_pipelines():
    """Initialize and register all pipelines"""
    
    # Register media pipelines
    from src.media_management.infrastructure.pipelines.upload_pipeline import register_media_pipelines
    register_media_pipelines()
    
    # Register text processing pipelines
    from src.text_processing.infrastructure.pipelines.extraction_pipeline import register_text_processing_pipelines
    register_text_processing_pipelines()
    
    # Register auth pipelines
    from src.auth.infrastructure.pipelines.auth_pipeline import register_auth_pipelines
    register_auth_pipelines()
    
    print("✅ All pipelines registered successfully")


# Example of combining multiple patterns
class HybridProcessingService:
    """Service that combines multiple design patterns"""
    
    def __init__(self):
        # Factory Pattern - create services
        self.media_service = EnhancedMediaUploadService()
        self.text_service = EnhancedTextExtractionService()
        self.auth_service = EnhancedAuthenticationService()
    
    @processing_operation("hybrid", "process_document_upload")
    async def process_document_upload(
        self,
        user_id: UUID,
        file_data: bytes,
        filename: str,
        extract_text: bool = True
    ) -> Dict[str, Any]:
        """
        Hybrid processing combining multiple pipelines:
        1. Media upload pipeline (Chain of Responsibility)
        2. Text extraction pipeline (Chain of Responsibility)
        3. Decorator patterns for cross-cutting concerns
        """
        results = {}
        
        # Step 1: Upload with media pipeline
        upload_result = await self.media_service.upload_with_validation(
            user_id=user_id,
            file_data=file_data,
            filename=filename
        )
        results["upload"] = upload_result
        
        # Step 2: Extract text if requested
        if extract_text:
            # Determine file type from filename
            file_type = self._detect_file_type(filename)
            
            extraction_result = await self.text_service.extract_text_with_pipeline(
                file_data=file_data,
                file_type=file_type,
                filename=filename
            )
            results["text_extraction"] = extraction_result
        
        return {
            "user_id": str(user_id),
            "filename": filename,
            "processing_completed": True,
            "results": results
        }
    
    def _detect_file_type(self, filename: str) -> str:
        """Helper method to detect file type"""
        extension = filename.lower().split('.')[-1]
        type_mapping = {
            'pdf': 'pdf',
            'docx': 'docx',
            'txt': 'txt',
            'md': 'md',
            'html': 'html'
        }
        return type_mapping.get(extension, 'txt')


# Example usage and testing
async def example_usage():
    """Example of using the enhanced services"""
    
    # Initialize pipelines
    await initialize_pipelines()
    
    # Create services
    media_service = EnhancedMediaUploadService()
    text_service = EnhancedTextExtractionService()
    auth_service = EnhancedAuthenticationService()
    monitoring_service = PipelineMonitoringService()
    
    # Example 1: Media upload with validation pipeline
    print("📁 Testing media upload with pipeline...")
    try:
        upload_result = await media_service.upload_with_validation(
            user_id=UUID("12345678-1234-5678-9012-123456789012"),
            file_data=b"fake file content",
            filename="test.pdf"
        )
        print(f"Upload result: {upload_result}")
    except Exception as e:
        print(f"Upload failed: {e}")
    
    # Example 2: Text extraction with pipeline
    print("\n📄 Testing text extraction with pipeline...")
    try:
        extraction_result = await text_service.extract_text_with_pipeline(
            file_data=b"Hello world content",
            file_type="txt",
            filename="test.txt"
        )
        print(f"Extraction result: {extraction_result}")
    except Exception as e:
        print(f"Extraction failed: {e}")
    
    # Example 3: Authentication with pipeline
    print("\n🔐 Testing authentication with pipeline...")
    try:
        auth_result = await auth_service.login_with_pipeline(
            username="testuser",
            password="password123",
            client_ip="192.168.1.1"
        )
        print(f"Auth result: {auth_result}")
    except Exception as e:
        print(f"Auth failed: {e}")
    
    # Example 4: Check pipeline metrics
    print("\n📊 Checking pipeline metrics...")
    metrics = await monitoring_service.get_pipeline_metrics()
    print(f"Pipeline metrics: {metrics}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())