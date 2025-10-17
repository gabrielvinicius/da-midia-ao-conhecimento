"""
Practical examples of Visitor Pattern usage with integration
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
import asyncio

# Import visitor decorators and integration
from src.shared.patterns.visitor_integration import (
    analytics_visitor, admin_visitor, media_visitor,
    IntegratedPatternFactory, VisitorManager, initialize_all_visitors
)

# Import traditional decorators
from src.shared.decorators.decorator_factory import read_operation, processing_operation


class EnhancedAnalyticsService:
    """Analytics service with visitor pattern integration"""
    
    @analytics_visitor(["statistics_visitor", "trend_analysis_visitor"])
    @processing_operation("analytics", "analyze_system_metrics")
    async def analyze_system_metrics(
        self,
        metrics: List[Dict[str, Any]],
        activities: List[Dict[str, Any]] = None,
        events: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Analyze system metrics using visitor pattern.
        
        Visitors will:
        - Calculate comprehensive statistics
        - Perform trend analysis
        - Detect anomalies
        """
        
        return {
            "metrics_processed": len(metrics),
            "activities_processed": len(activities or []),
            "events_processed": len(events or []),
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    @analytics_visitor(["anomaly_detection_visitor"])
    @processing_operation("analytics", "detect_anomalies")
    async def detect_system_anomalies(
        self,
        metrics: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Detect anomalies in system metrics"""
        
        return {
            "metrics_analyzed": len(metrics),
            "anomaly_detection_completed": True
        }


class EnhancedAdminService:
    """Admin service with visitor pattern integration"""
    
    @admin_visitor(["security_audit_visitor", "compliance_check_visitor"])
    @processing_operation("admin", "security_compliance_audit")
    async def perform_security_compliance_audit(
        self,
        users: List[Dict[str, Any]],
        media: List[Dict[str, Any]] = None,
        resources: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Perform comprehensive security and compliance audit.
        
        Visitors will:
        - Audit security vulnerabilities
        - Check compliance violations
        - Generate recommendations
        """
        
        return {
            "users_audited": len(users),
            "media_items_audited": len(media or []),
            "resources_audited": len(resources or []),
            "audit_timestamp": datetime.now().isoformat()
        }
    
    @admin_visitor(["system_cleanup_visitor"])
    @processing_operation("admin", "system_cleanup_analysis")
    async def analyze_cleanup_opportunities(
        self,
        users: List[Dict[str, Any]],
        media: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Analyze system cleanup opportunities"""
        
        return {
            "cleanup_analysis_completed": True,
            "users_analyzed": len(users),
            "media_analyzed": len(media or [])
        }


class EnhancedMediaService:
    """Media service with visitor pattern integration"""
    
    @media_visitor(["media_analysis_visitor", "media_optimization_visitor"])
    @processing_operation("media", "comprehensive_media_analysis")
    async def analyze_media_library(
        self,
        media_files: List[Dict[str, Any]],
        processing_results: List[Dict[str, Any]] = None,
        collections: List[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive media library analysis.
        
        Visitors will:
        - Analyze file statistics and usage patterns
        - Identify optimization opportunities
        - Calculate storage savings potential
        """
        
        return {
            "media_files_analyzed": len(media_files),
            "processing_results_analyzed": len(processing_results or []),
            "collections_analyzed": len(collections or []),
            "analysis_timestamp": datetime.now().isoformat()
        }
    
    @media_visitor(["media_transformation_visitor"])
    @processing_operation("media", "transform_media_data")
    async def transform_media_metadata(
        self,
        media_files: List[Dict[str, Any]],
        transformations: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Transform media metadata using visitor pattern"""
        
        return {
            "files_processed": len(media_files),
            "transformations_applied": transformations or {},
            "transformation_completed": True
        }


# Example usage and demonstration
async def demonstrate_visitor_patterns():
    """Demonstrate visitor pattern usage"""
    
    # Initialize all visitors
    await initialize_all_visitors()
    
    print("🔍 Visitor Pattern Demonstration")
    print("=" * 50)
    
    # Create services
    analytics_service = EnhancedAnalyticsService()
    admin_service = EnhancedAdminService()
    media_service = EnhancedMediaService()
    
    # Example 1: Analytics with visitors
    print("\n📊 Analytics Analysis with Visitors")
    try:
        # Mock metrics data
        metrics_data = [
            {
                "name": "cpu_usage",
                "value": 75.5,
                "timestamp": datetime.now(),
                "category": "performance",
                "tags": {"host": "server1"}
            },
            {
                "name": "memory_usage", 
                "value": 85.2,
                "timestamp": datetime.now(),
                "category": "performance",
                "tags": {"host": "server1"}
            }
        ]
        
        activities_data = [
            {
                "user_id": "user123",
                "action": "login",
                "timestamp": datetime.now(),
                "metadata": {"ip": "192.168.1.1"}
            }
        ]
        
        analytics_result = await analytics_service.analyze_system_metrics(
            metrics=metrics_data,
            activities=activities_data
        )
        
        print(f"Analytics result: {analytics_result}")
        
    except Exception as e:
        print(f"Analytics analysis failed: {e}")
    
    # Example 2: Admin audit with visitors
    print("\n🔐 Security Audit with Visitors")
    try:
        # Mock user data
        users_data = [
            {
                "user_id": "admin1",
                "username": "admin",
                "email": "admin@example.com",
                "role": "admin",
                "is_active": True,
                "created_at": datetime.now() - timedelta(days=100),
                "last_login": datetime.now() - timedelta(days=1),
                "permissions": ["user_management", "system_admin"]
            },
            {
                "user_id": "user1",
                "username": "testuser",
                "email": "user@example.com", 
                "role": "user",
                "is_active": False,
                "created_at": datetime.now() - timedelta(days=200),
                "last_login": datetime.now() - timedelta(days=100),
                "permissions": []
            }
        ]
        
        audit_result = await admin_service.perform_security_compliance_audit(
            users=users_data
        )
        
        print(f"Audit result: {audit_result}")
        
    except Exception as e:
        print(f"Security audit failed: {e}")
    
    # Example 3: Media analysis with visitors
    print("\n🎬 Media Analysis with Visitors")
    try:
        # Mock media data
        media_files_data = [
            {
                "file_id": "media1",
                "user_id": "user1",
                "filename": "video.mp4",
                "original_filename": "my_video.mp4",
                "file_size": 50 * 1024 * 1024,  # 50MB
                "mime_type": "video/mp4",
                "media_type": "video",
                "processing_status": "completed",
                "upload_date": datetime.now() - timedelta(days=30),
                "last_accessed": datetime.now() - timedelta(days=5),
                "tags": ["vacation", "family"]
            },
            {
                "file_id": "media2",
                "user_id": "user2", 
                "filename": "large_video.mp4",
                "original_filename": "huge_file.mp4",
                "file_size": 200 * 1024 * 1024,  # 200MB
                "mime_type": "video/mp4",
                "media_type": "video",
                "processing_status": "failed",
                "upload_date": datetime.now() - timedelta(days=60),
                "last_accessed": None,
                "tags": []
            }
        ]
        
        media_result = await media_service.analyze_media_library(
            media_files=media_files_data
        )
        
        print(f"Media analysis result: {media_result}")
        
    except Exception as e:
        print(f"Media analysis failed: {e}")
    
    # Example 4: Visitor management and monitoring
    print("\n📋 Visitor Management")
    try:
        available_visitors = VisitorManager.get_available_visitors()
        print(f"Available visitors: {available_visitors}")
        
    except Exception as e:
        print(f"Visitor management failed: {e}")


# Advanced visitor composition example
class HybridAnalysisService:
    """Service that combines multiple visitor patterns"""
    
    @analytics_visitor(["statistics_visitor", "anomaly_detection_visitor"])
    @admin_visitor(["security_audit_visitor"])
    @processing_operation("hybrid", "comprehensive_system_analysis")
    async def perform_comprehensive_analysis(
        self,
        metrics: List[Dict[str, Any]],
        users: List[Dict[str, Any]],
        media_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Comprehensive system analysis using multiple visitor patterns.
        
        This demonstrates how multiple visitor decorators can be stacked
        to provide comprehensive analysis across different domains.
        """
        
        return {
            "comprehensive_analysis": True,
            "metrics_count": len(metrics),
            "users_count": len(users),
            "media_count": len(media_files),
            "analysis_domains": ["analytics", "security", "media"],
            "timestamp": datetime.now().isoformat()
        }


# Factory-based visitor service creation
async def demonstrate_factory_integration():
    """Demonstrate factory-based visitor service creation"""
    
    print("\n🏭 Factory-Based Visitor Services")
    
    # Create integrated services using factory
    analytics_service = IntegratedPatternFactory.create_analytics_service_with_visitors()
    admin_service = IntegratedPatternFactory.create_admin_service_with_visitors()
    media_service = IntegratedPatternFactory.create_media_service_with_visitors()
    
    # Example usage
    try:
        # Analytics service with visitors
        analytics_result = await analytics_service.analyze_comprehensive_data(
            metrics=[{"name": "test_metric", "value": 100, "timestamp": datetime.now(), "category": "test"}],
            activities=[{"user_id": "test", "action": "test", "timestamp": datetime.now()}],
            events=[{"event_type": "test", "severity": "info", "timestamp": datetime.now(), 
                    "component": "test", "message": "test event"}]
        )
        print(f"Factory analytics result: {analytics_result}")
        
    except Exception as e:
        print(f"Factory analytics failed: {e}")


# Performance monitoring for visitors
class VisitorPerformanceMonitor:
    """Monitor visitor pattern performance"""
    
    @read_operation("monitoring", "get_visitor_performance")
    async def get_visitor_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for visitor operations"""
        
        available_visitors = VisitorManager.get_available_visitors()
        
        return {
            "total_visitor_types": sum(len(visitors) for visitors in available_visitors.values()),
            "visitors_by_category": {k: len(v) for k, v in available_visitors.items()},
            "performance_status": "monitoring_active",
            "recommendations": [
                "Monitor visitor execution times",
                "Track visitor error rates",
                "Optimize data structure traversal"
            ]
        }


# Main demonstration function
async def main():
    """Main demonstration of visitor patterns"""
    
    print("🚀 Starting Visitor Pattern Demonstration")
    
    # Basic visitor pattern demonstration
    await demonstrate_visitor_patterns()
    
    # Factory integration demonstration
    await demonstrate_factory_integration()
    
    # Performance monitoring
    monitor = VisitorPerformanceMonitor()
    performance_metrics = await monitor.get_visitor_performance_metrics()
    print(f"\n📈 Performance Metrics: {performance_metrics}")
    
    print("\n✅ Visitor Pattern demonstration completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())