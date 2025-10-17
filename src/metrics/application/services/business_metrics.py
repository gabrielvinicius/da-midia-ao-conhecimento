"""
Business Metrics Service - Single Responsibility: Business metrics tracking
Follows SRP by handling only business-related metrics.
"""
from typing import Dict, Any
from uuid import UUID
import structlog

from src.metrics.domain.interfaces import IBusinessMetrics, IMetricsProvider

logger = structlog.get_logger(__name__)


class BusinessMetrics(IBusinessMetrics):
    """
    Service responsible ONLY for business metrics operations.
    
    Single Responsibility: Handle business KPIs and revenue metrics.
    Open/Closed: Extensible for new business metrics.
    Dependency Inversion: Depends on metrics provider abstraction.
    """
    
    def __init__(self, metrics_provider: IMetricsProvider):
        self.metrics_provider = metrics_provider
    
    def track_media_upload(self, status: str, media_type: str, user_id: UUID) -> None:
        """
        Track media upload events with business context.
        
        Args:
            status: Upload status (success, failed)
            media_type: Type of media (video, audio, text)
            user_id: User performing the upload
        """
        labels = {
            "status": status,
            "media_type": media_type,
            "user_id": str(user_id)
        }
        
        self.metrics_provider.increment_counter("MEDIA_UPLOADS_TOTAL", labels)
        
        # Track revenue-impacting uploads (successful ones)
        if status == "success":
            self.metrics_provider.increment_counter("REVENUE_GENERATING_UPLOADS", labels)
        
        logger.info(
            "business.media_upload_tracked",
            status=status,
            media_type=media_type,
            user_id=str(user_id)
        )
    
    def track_processing_completion(self, operation: str, status: str, duration: float) -> None:
        """
        Track processing completion events for business analysis.
        
        Args:
            operation: Type of operation (transcription, summarization)
            status: Completion status (success, failed)
            duration: Processing duration in seconds
        """
        labels = {
            "operation": operation,
            "status": status
        }
        
        # Track completion counts
        self.metrics_provider.increment_counter("PROCESSING_COMPLETIONS_TOTAL", labels)
        
        # Track processing duration for business efficiency
        self.metrics_provider.observe_histogram("PROCESSING_DURATION_BUSINESS", duration, labels)
        
        # Calculate cost metrics (simplified)
        estimated_cost = self._calculate_processing_cost(operation, duration)
        cost_labels = {"operation": operation}
        self.metrics_provider.observe_histogram("PROCESSING_COST_USD", estimated_cost, cost_labels)
        
        logger.info(
            "business.processing_completion_tracked",
            operation=operation,
            status=status,
            duration=duration,
            estimated_cost=estimated_cost
        )
    
    def track_user_activity(self, user_id: UUID, action: str, resource_type: str) -> None:
        """
        Track user activity for engagement metrics.
        
        Args:
            user_id: User performing the action
            action: Action performed (upload, view, download)
            resource_type: Type of resource (media, summary, transcription)
        """
        labels = {
            "user_id": str(user_id),
            "action": action,
            "resource_type": resource_type
        }
        
        # Track overall user activity
        self.metrics_provider.increment_counter("USER_ACTIVITIES_TOTAL", labels)
        
        # Track unique active users
        user_labels = {"user_id": str(user_id)}
        self.metrics_provider.set_gauge("ACTIVE_USERS_CURRENT", 1.0, user_labels)
        
        # Track engagement by action type
        engagement_labels = {"action": action, "resource_type": resource_type}
        self.metrics_provider.increment_counter("USER_ENGAGEMENT_TOTAL", engagement_labels)
        
        logger.debug(
            "business.user_activity_tracked",
            user_id=str(user_id),
            action=action,
            resource_type=resource_type
        )
    
    def track_revenue_event(self, amount: float, currency: str, user_id: UUID) -> None:
        """
        Track revenue-related events.
        
        Args:
            amount: Revenue amount
            currency: Currency code (USD, EUR, etc.)
            user_id: User generating the revenue
        """
        labels = {
            "currency": currency,
            "user_id": str(user_id)
        }
        
        # Track revenue amount
        self.metrics_provider.observe_histogram("REVENUE_AMOUNT", amount, labels)
        
        # Track revenue events count
        self.metrics_provider.increment_counter("REVENUE_EVENTS_TOTAL", labels)
        
        # Update total revenue gauge
        current_total = self.metrics_provider.get_metric_value("TOTAL_REVENUE_USD") or 0
        if currency == "USD":
            new_total = current_total + amount
            self.metrics_provider.set_gauge("TOTAL_REVENUE_USD", new_total)
        
        logger.info(
            "business.revenue_tracked",
            amount=amount,
            currency=currency,
            user_id=str(user_id)
        )
    
    def get_business_kpis(self) -> Dict[str, Any]:
        """
        Get key business performance indicators.
        
        Returns:
            Dictionary with current business KPIs
        """
        try:
            # Get current metric values
            total_uploads = self.metrics_provider.get_metric_value("MEDIA_UPLOADS_TOTAL") or 0
            successful_uploads = self.metrics_provider.get_metric_value("REVENUE_GENERATING_UPLOADS") or 0
            total_revenue = self.metrics_provider.get_metric_value("TOTAL_REVENUE_USD") or 0
            processing_completions = self.metrics_provider.get_metric_value("PROCESSING_COMPLETIONS_TOTAL") or 0
            
            # Calculate KPIs
            upload_success_rate = (successful_uploads / total_uploads * 100) if total_uploads > 0 else 0
            average_revenue_per_upload = (total_revenue / successful_uploads) if successful_uploads > 0 else 0
            
            kpis = {
                "total_uploads": total_uploads,
                "successful_uploads": successful_uploads,
                "upload_success_rate_percent": round(upload_success_rate, 2),
                "total_revenue_usd": total_revenue,
                "average_revenue_per_upload": round(average_revenue_per_upload, 2),
                "processing_completions": processing_completions,
                "calculated_at": "2024-01-01T00:00:00Z"  # Would use actual timestamp
            }
            
            logger.info("business.kpis_calculated", kpis=kpis)
            return kpis
            
        except Exception as e:
            logger.error("business.kpis_calculation_failed", error=str(e))
            return {
                "error": "Failed to calculate KPIs",
                "calculated_at": "2024-01-01T00:00:00Z"
            }
    
    def _calculate_processing_cost(self, operation: str, duration: float) -> float:
        """
        Calculate estimated processing cost based on operation and duration.
        
        Args:
            operation: Type of operation
            duration: Processing duration in seconds
            
        Returns:
            Estimated cost in USD
        """
        # Simplified cost calculation (in real world, this would be more complex)
        cost_per_second = {
            "transcription": 0.001,  # $0.001 per second
            "summarization": 0.0005,  # $0.0005 per second
            "sentiment_analysis": 0.0002,  # $0.0002 per second
            "topic_modeling": 0.0003   # $0.0003 per second
        }
        
        rate = cost_per_second.get(operation, 0.0001)  # Default rate
        return duration * rate
    
    def track_feature_usage(self, feature_name: str, user_id: UUID) -> None:
        """
        Track usage of specific features for product analytics.
        
        Args:
            feature_name: Name of the feature used
            user_id: User using the feature
        """
        labels = {
            "feature": feature_name,
            "user_id": str(user_id)
        }
        
        self.metrics_provider.increment_counter("FEATURE_USAGE_TOTAL", labels)
        
        # Track unique feature users
        feature_labels = {"feature": feature_name}
        self.metrics_provider.increment_counter("FEATURE_UNIQUE_USERS", feature_labels)
        
        logger.debug(
            "business.feature_usage_tracked",
            feature=feature_name,
            user_id=str(user_id)
        )
    
    def track_subscription_event(self, event_type: str, plan: str, user_id: UUID) -> None:
        """
        Track subscription-related events.
        
        Args:
            event_type: Type of event (subscribe, unsubscribe, upgrade, downgrade)
            plan: Subscription plan (basic, premium, enterprise)
            user_id: User involved in the event
        """
        labels = {
            "event_type": event_type,
            "plan": plan,
            "user_id": str(user_id)
        }
        
        self.metrics_provider.increment_counter("SUBSCRIPTION_EVENTS_TOTAL", labels)
        
        # Track current subscriptions by plan
        if event_type == "subscribe":
            plan_labels = {"plan": plan}
            current_count = self.metrics_provider.get_metric_value("ACTIVE_SUBSCRIPTIONS", plan_labels) or 0
            self.metrics_provider.set_gauge("ACTIVE_SUBSCRIPTIONS", current_count + 1, plan_labels)
        elif event_type == "unsubscribe":
            plan_labels = {"plan": plan}
            current_count = self.metrics_provider.get_metric_value("ACTIVE_SUBSCRIPTIONS", plan_labels) or 0
            self.metrics_provider.set_gauge("ACTIVE_SUBSCRIPTIONS", max(0, current_count - 1), plan_labels)
        
        logger.info(
            "business.subscription_event_tracked",
            event_type=event_type,
            plan=plan,
            user_id=str(user_id)
        )