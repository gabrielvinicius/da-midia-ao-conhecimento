"""
Media Management Visitors using Visitor Pattern for media operations
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import mimetypes

from src.shared.patterns.visitor import (
    BaseVisitor, IVisitable, LeafElement, CompositeElement, 
    VisitorResult, VisitorRegistry
)


class MediaType(str, Enum):
    """Media types"""
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    OTHER = "other"


class ProcessingStatus(str, Enum):
    """Processing status"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


@dataclass
class MediaFile:
    """Media file data structure"""
    file_id: str
    user_id: str
    filename: str
    original_filename: str
    file_size: int
    mime_type: str
    media_type: MediaType
    processing_status: ProcessingStatus
    upload_date: datetime
    last_accessed: Optional[datetime] = None
    transcription_id: Optional[str] = None
    summary_id: Optional[str] = None
    tags: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ProcessingResult:
    """Processing result data"""
    result_id: str
    media_file_id: str
    processing_type: str
    status: ProcessingStatus
    result_data: Dict[str, Any]
    processing_time: float
    created_at: datetime
    error_message: Optional[str] = None


@dataclass
class MediaCollection:
    """Media collection data"""
    collection_id: str
    name: str
    description: str
    owner_id: str
    media_files: List[str]
    created_at: datetime
    is_public: bool = False
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


class MediaFileElement(LeafElement):
    """Visitable element for media files"""
    
    def __init__(self, media_file: MediaFile):
        super().__init__(f"MediaFile_{media_file.filename}", media_file)
        self.media_file = media_file
    
    def get_element_type(self) -> str:
        return "MediaFile"


class ProcessingResultElement(LeafElement):
    """Visitable element for processing results"""
    
    def __init__(self, result: ProcessingResult):
        super().__init__(f"ProcessingResult_{result.processing_type}", result)
        self.processing_result = result
    
    def get_element_type(self) -> str:
        return "ProcessingResult"


class MediaCollectionElement(CompositeElement):
    """Visitable element for media collections"""
    
    def __init__(self, collection: MediaCollection):
        super().__init__(f"Collection_{collection.name}")
        self.collection = collection
        self.media_elements: List[MediaFileElement] = []
    
    def add_media_file(self, media_file: MediaFile) -> None:
        """Add media file to collection"""
        element = MediaFileElement(media_file)
        self.add_child(element)
        self.media_elements.append(element)
    
    def get_element_type(self) -> str:
        return "MediaCollection"


class MediaLibraryContainer(CompositeElement):
    """Container for entire media library"""
    
    def __init__(self, name: str):
        super().__init__(name)
        self.media_files: List[MediaFileElement] = []
        self.processing_results: List[ProcessingResultElement] = []
        self.collections: List[MediaCollectionElement] = []
    
    def add_media_file(self, media_file: MediaFile) -> None:
        """Add media file to library"""
        element = MediaFileElement(media_file)
        self.add_child(element)
        self.media_files.append(element)
    
    def add_processing_result(self, result: ProcessingResult) -> None:
        """Add processing result to library"""
        element = ProcessingResultElement(result)
        self.add_child(element)
        self.processing_results.append(element)
    
    def add_collection(self, collection: MediaCollection) -> None:
        """Add collection to library"""
        element = MediaCollectionElement(collection)
        self.add_child(element)
        self.collections.append(element)
    
    def get_element_type(self) -> str:
        return "MediaLibraryContainer"


class MediaAnalysisVisitor(BaseVisitor[Dict[str, Any]]):
    """Visitor for comprehensive media analysis"""
    
    def __init__(self):
        super().__init__("MediaAnalysisVisitor")
        self.file_stats = {
            "total_files": 0,
            "total_size": 0,
            "by_type": {},
            "by_status": {},
            "by_user": {}
        }
        self.processing_stats = {}
        self.collection_stats = {}
    
    def visit_MediaFile(self, element: MediaFileElement) -> Dict[str, Any]:
        """Analyze media file"""
        media = element.media_file
        
        # Update file statistics
        self.file_stats["total_files"] += 1
        self.file_stats["total_size"] += media.file_size
        
        # Count by type
        media_type = media.media_type.value
        if media_type not in self.file_stats["by_type"]:
            self.file_stats["by_type"][media_type] = {"count": 0, "size": 0}
        self.file_stats["by_type"][media_type]["count"] += 1
        self.file_stats["by_type"][media_type]["size"] += media.file_size
        
        # Count by status
        status = media.processing_status.value
        if status not in self.file_stats["by_status"]:
            self.file_stats["by_status"][status] = 0
        self.file_stats["by_status"][status] += 1
        
        # Count by user
        if media.user_id not in self.file_stats["by_user"]:
            self.file_stats["by_user"][media.user_id] = {"count": 0, "size": 0}
        self.file_stats["by_user"][media.user_id]["count"] += 1
        self.file_stats["by_user"][media.user_id]["size"] += media.file_size
        
        # Analyze file characteristics
        analysis = {
            "file_id": media.file_id,
            "media_type": media_type,
            "file_size_mb": round(media.file_size / (1024 * 1024), 2),
            "age_days": (datetime.now() - media.upload_date).days,
            "has_transcription": media.transcription_id is not None,
            "has_summary": media.summary_id is not None,
            "tag_count": len(media.tags),
            "access_frequency": self._calculate_access_frequency(media)
        }
        
        return analysis
    
    def visit_ProcessingResult(self, element: ProcessingResultElement) -> Dict[str, Any]:
        """Analyze processing result"""
        result = element.processing_result
        
        # Update processing statistics
        proc_type = result.processing_type
        if proc_type not in self.processing_stats:
            self.processing_stats[proc_type] = {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "avg_time": 0,
                "total_time": 0
            }
        
        stats = self.processing_stats[proc_type]
        stats["total"] += 1
        stats["total_time"] += result.processing_time
        
        if result.status == ProcessingStatus.COMPLETED:
            stats["successful"] += 1
        elif result.status == ProcessingStatus.FAILED:
            stats["failed"] += 1
        
        stats["avg_time"] = stats["total_time"] / stats["total"]
        
        return {
            "result_id": result.result_id,
            "processing_type": proc_type,
            "status": result.status.value,
            "processing_time": result.processing_time,
            "success_rate": stats["successful"] / stats["total"] if stats["total"] > 0 else 0
        }
    
    def visit_MediaCollection(self, element: MediaCollectionElement) -> Dict[str, Any]:
        """Analyze media collection"""
        collection = element.collection
        
        # Collection statistics
        collection_analysis = {
            "collection_id": collection.collection_id,
            "name": collection.name,
            "media_count": len(collection.media_files),
            "is_public": collection.is_public,
            "tag_count": len(collection.tags),
            "age_days": (datetime.now() - collection.created_at).days
        }
        
        self.collection_stats[collection.collection_id] = collection_analysis
        
        return collection_analysis
    
    def visit_MediaLibraryContainer(self, element: MediaLibraryContainer) -> Dict[str, Any]:
        """Analyze entire media library"""
        return {
            "library_name": element.name,
            "total_media_files": len(element.media_files),
            "total_processing_results": len(element.processing_results),
            "total_collections": len(element.collections),
            "total_elements": len(element.children)
        }
    
    def _create_default_result(self, element: IVisitable) -> Dict[str, Any]:
        return {"type": "media_unknown"}
    
    def _calculate_access_frequency(self, media: MediaFile) -> str:
        """Calculate access frequency category"""
        if not media.last_accessed:
            return "never"
        
        days_since_access = (datetime.now() - media.last_accessed).days
        
        if days_since_access <= 7:
            return "frequent"
        elif days_since_access <= 30:
            return "regular"
        elif days_since_access <= 90:
            return "occasional"
        else:
            return "rare"
    
    def get_comprehensive_analysis(self) -> Dict[str, Any]:
        """Get comprehensive media analysis"""
        
        # Calculate derived statistics
        avg_file_size = (
            self.file_stats["total_size"] / self.file_stats["total_files"]
            if self.file_stats["total_files"] > 0 else 0
        )
        
        # Processing success rates
        overall_processing_stats = {}
        for proc_type, stats in self.processing_stats.items():
            success_rate = stats["successful"] / stats["total"] if stats["total"] > 0 else 0
            overall_processing_stats[proc_type] = {
                "success_rate": success_rate,
                "avg_processing_time": stats["avg_time"],
                "total_processed": stats["total"]
            }
        
        return {
            "file_statistics": {
                **self.file_stats,
                "avg_file_size_mb": round(avg_file_size / (1024 * 1024), 2),
                "total_size_gb": round(self.file_stats["total_size"] / (1024 * 1024 * 1024), 2)
            },
            "processing_statistics": overall_processing_stats,
            "collection_statistics": {
                "total_collections": len(self.collection_stats),
                "public_collections": sum(1 for c in self.collection_stats.values() if c["is_public"]),
                "avg_collection_size": (
                    sum(c["media_count"] for c in self.collection_stats.values()) / 
                    len(self.collection_stats) if self.collection_stats else 0
                )
            },
            "recommendations": self._generate_recommendations()
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        # Storage recommendations
        if self.file_stats["total_size"] > 10 * 1024 * 1024 * 1024:  # 10GB
            recommendations.append("Consider implementing storage archiving policy")
        
        # Processing recommendations
        failed_processing = sum(
            stats["failed"] for stats in self.processing_stats.values()
        )
        if failed_processing > 0:
            recommendations.append("Review and retry failed processing jobs")
        
        # Usage recommendations
        user_count = len(self.file_stats["by_user"])
        if user_count > 0:
            avg_files_per_user = self.file_stats["total_files"] / user_count
            if avg_files_per_user > 100:
                recommendations.append("Consider user storage quotas")
        
        return recommendations


class MediaOptimizationVisitor(BaseVisitor[Dict[str, Any]]):
    """Visitor for media optimization opportunities"""
    
    def __init__(self):
        super().__init__("MediaOptimizationVisitor")
        self.optimization_opportunities = []
        self.storage_savings = 0
    
    def visit_MediaFile(self, element: MediaFileElement) -> Dict[str, Any]:
        """Identify optimization opportunities for media files"""
        media = element.media_file
        opportunities = []
        
        # Large file optimization
        if media.file_size > 100 * 1024 * 1024:  # 100MB
            opportunities.append({
                "type": "compression",
                "reason": "Large file size",
                "potential_savings": media.file_size * 0.3,  # Estimate 30% savings
                "priority": "medium"
            })
        
        # Unused file optimization
        if media.last_accessed:
            days_since_access = (datetime.now() - media.last_accessed).days
            if days_since_access > 365:  # 1 year
                opportunities.append({
                    "type": "archival",
                    "reason": "Not accessed for over 1 year",
                    "potential_savings": media.file_size,
                    "priority": "low"
                })
        
        # Duplicate detection opportunity
        if len(media.tags) == 0 and media.processing_status == ProcessingStatus.COMPLETED:
            opportunities.append({
                "type": "tagging",
                "reason": "Missing tags for processed file",
                "potential_savings": 0,
                "priority": "low"
            })
        
        # Failed processing cleanup
        if media.processing_status == ProcessingStatus.FAILED:
            age_days = (datetime.now() - media.upload_date).days
            if age_days > 30:
                opportunities.append({
                    "type": "cleanup",
                    "reason": "Failed processing older than 30 days",
                    "potential_savings": media.file_size,
                    "priority": "high"
                })
        
        # Video optimization
        if media.media_type == MediaType.VIDEO and media.file_size > 50 * 1024 * 1024:
            opportunities.append({
                "type": "video_optimization",
                "reason": "Large video file",
                "potential_savings": media.file_size * 0.5,  # Estimate 50% savings
                "priority": "medium"
            })
        
        # Add opportunities to global list
        for opp in opportunities:
            opp["file_id"] = media.file_id
            opp["filename"] = media.filename
            opp["current_size"] = media.file_size
            self.optimization_opportunities.append(opp)
            self.storage_savings += opp["potential_savings"]
        
        return {
            "file_id": media.file_id,
            "optimization_opportunities": len(opportunities),
            "potential_savings": sum(opp["potential_savings"] for opp in opportunities)
        }
    
    def visit_MediaCollection(self, element: MediaCollectionElement) -> Dict[str, Any]:
        """Identify collection optimization opportunities"""
        collection = element.collection
        
        # Empty collection cleanup
        if len(collection.media_files) == 0:
            age_days = (datetime.now() - collection.created_at).days
            if age_days > 90:
                self.optimization_opportunities.append({
                    "type": "collection_cleanup",
                    "collection_id": collection.collection_id,
                    "reason": "Empty collection older than 90 days",
                    "potential_savings": 0,
                    "priority": "low"
                })
        
        return {
            "collection_id": collection.collection_id,
            "needs_cleanup": len(collection.media_files) == 0
        }
    
    def _create_default_result(self, element: IVisitable) -> Dict[str, Any]:
        return {"type": "optimization_unknown"}
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """Generate optimization report"""
        
        # Group opportunities by type and priority
        by_type = {}
        by_priority = {"high": [], "medium": [], "low": []}
        
        for opp in self.optimization_opportunities:
            opp_type = opp["type"]
            priority = opp["priority"]
            
            if opp_type not in by_type:
                by_type[opp_type] = []
            by_type[opp_type].append(opp)
            by_priority[priority].append(opp)
        
        # Calculate potential savings by type
        savings_by_type = {}
        for opp_type, opportunities in by_type.items():
            savings_by_type[opp_type] = sum(opp["potential_savings"] for opp in opportunities)
        
        return {
            "total_opportunities": len(self.optimization_opportunities),
            "opportunities_by_type": {k: len(v) for k, v in by_type.items()},
            "opportunities_by_priority": {k: len(v) for k, v in by_priority.items()},
            "potential_storage_savings_bytes": self.storage_savings,
            "potential_storage_savings_gb": round(self.storage_savings / (1024**3), 2),
            "savings_by_type_gb": {
                k: round(v / (1024**3), 2) for k, v in savings_by_type.items()
            },
            "detailed_opportunities": by_type,
            "top_opportunities": sorted(
                self.optimization_opportunities,
                key=lambda x: x["potential_savings"],
                reverse=True
            )[:10],
            "recommendations": self._generate_optimization_recommendations()
        }
    
    def _generate_optimization_recommendations(self) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []
        
        if self.storage_savings > 1024**3:  # 1GB
            recommendations.append("Significant storage savings available - prioritize optimization")
        
        high_priority_count = sum(
            1 for opp in self.optimization_opportunities if opp["priority"] == "high"
        )
        if high_priority_count > 0:
            recommendations.append(f"Address {high_priority_count} high-priority optimization opportunities")
        
        recommendations.extend([
            "Implement automated optimization policies",
            "Regular cleanup of failed processing jobs",
            "Consider implementing file compression for large media",
            "Archive old, unused files to cheaper storage"
        ])
        
        return recommendations


class MediaTransformationVisitor(BaseVisitor[Dict[str, Any]]):
    """Visitor for applying transformations to media data"""
    
    def __init__(self, transformations: Dict[str, Any] = None):
        super().__init__("MediaTransformationVisitor")
        self.transformations = transformations or {}
        self.transformed_files = []
        self.transformation_results = {}
    
    def visit_MediaFile(self, element: MediaFileElement) -> Dict[str, Any]:
        """Apply transformations to media file"""
        media = element.media_file
        applied_transformations = []
        
        # Tag normalization
        if "normalize_tags" in self.transformations:
            normalized_tags = [tag.lower().strip() for tag in media.tags]
            normalized_tags = list(set(normalized_tags))  # Remove duplicates
            applied_transformations.append("tag_normalization")
        
        # Status update based on age
        if "update_old_processing" in self.transformations:
            age_days = (datetime.now() - media.upload_date).days
            if media.processing_status == ProcessingStatus.PROCESSING and age_days > 7:
                applied_transformations.append("status_update_to_failed")
        
        # Add missing metadata
        if "add_metadata" in self.transformations:
            if "file_extension" not in media.metadata:
                extension = media.filename.split(".")[-1] if "." in media.filename else ""
                applied_transformations.append("add_file_extension_metadata")
        
        # File type correction
        if "correct_media_type" in self.transformations:
            detected_type = self._detect_media_type_from_mime(media.mime_type)
            if detected_type != media.media_type:
                applied_transformations.append("media_type_correction")
        
        if applied_transformations:
            self.transformed_files.append(media.file_id)
            self.transformation_results[media.file_id] = applied_transformations
        
        return {
            "file_id": media.file_id,
            "transformations_applied": applied_transformations,
            "transformation_count": len(applied_transformations)
        }
    
    def _create_default_result(self, element: IVisitable) -> Dict[str, Any]:
        return {"type": "transformation_unknown"}
    
    def _detect_media_type_from_mime(self, mime_type: str) -> MediaType:
        """Detect media type from MIME type"""
        if mime_type.startswith("image/"):
            return MediaType.IMAGE
        elif mime_type.startswith("video/"):
            return MediaType.VIDEO
        elif mime_type.startswith("audio/"):
            return MediaType.AUDIO
        elif mime_type in ["application/pdf", "text/plain", "application/msword"]:
            return MediaType.DOCUMENT
        else:
            return MediaType.OTHER
    
    def get_transformation_report(self) -> Dict[str, Any]:
        """Generate transformation report"""
        
        transformation_counts = {}
        for file_transforms in self.transformation_results.values():
            for transform in file_transforms:
                transformation_counts[transform] = transformation_counts.get(transform, 0) + 1
        
        return {
            "total_files_transformed": len(self.transformed_files),
            "transformation_types_applied": transformation_counts,
            "transformation_details": self.transformation_results,
            "success_rate": len(self.transformed_files) / self.result.visited_count if self.result.visited_count > 0 else 0
        }


# Register media management visitors
def register_media_visitors():
    """Register all media management visitors"""
    
    VisitorRegistry.register_visitor(
        "media_analysis_visitor",
        MediaAnalysisVisitor,
        "media"
    )
    
    VisitorRegistry.register_visitor(
        "media_optimization_visitor",
        MediaOptimizationVisitor,
        "media"
    )
    
    VisitorRegistry.register_visitor(
        "media_transformation_visitor",
        MediaTransformationVisitor,
        "media"
    )