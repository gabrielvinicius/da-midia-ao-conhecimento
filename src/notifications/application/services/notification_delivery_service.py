"""
Notification Delivery Service - Single Responsibility: Notification delivery coordination
Follows SRP by handling only delivery orchestration across channels.
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timedelta
import structlog

from src.notifications.domain.interfaces import (
    INotificationDeliveryService, INotificationSender, INotificationPreferences,
    IWebSocketManager, DeliveryChannel
)
from src.notifications.domain.notification import Notification, NotificationStatus

logger = structlog.get_logger(__name__)


class NotificationDeliveryService(INotificationDeliveryService):
    """
    Service responsible ONLY for coordinating notification delivery across channels.
    
    Single Responsibility: Handle delivery orchestration and channel management.
    Open/Closed: Extensible through new delivery channels.
    Dependency Inversion: Depends on abstractions for senders and preferences.
    """
    
    def __init__(
        self,
        preferences_service: INotificationPreferences,
        websocket_manager: IWebSocketManager,
        email_sender: Optional[INotificationSender] = None,
        sms_sender: Optional[INotificationSender] = None,
        push_sender: Optional[INotificationSender] = None
    ):
        self.preferences_service = preferences_service
        self.websocket_manager = websocket_manager
        self.senders = {}
        
        # Register available senders
        if email_sender:
            self.senders[DeliveryChannel.EMAIL] = email_sender
        if sms_sender:
            self.senders[DeliveryChannel.SMS] = sms_sender
        if push_sender:
            self.senders[DeliveryChannel.PUSH] = push_sender
        
        # WebSocket is handled directly
        self.senders[DeliveryChannel.WEBSOCKET] = self.websocket_manager
    
    async def deliver_notification(
        self,
        notification: Notification,
        preferred_channels: List[DeliveryChannel],
        fallback_channels: Optional[List[DeliveryChannel]] = None
    ) -> Dict[DeliveryChannel, bool]:
        """
        Deliver notification through preferred channels with fallback.
        
        Args:
            notification: Notification to deliver
            preferred_channels: Preferred delivery channels
            fallback_channels: Fallback channels if preferred fail
            
        Returns:
            Dict mapping channels to delivery success status
        """
        results = {}
        delivered = False
        
        try:
            # Get user preferences
            user_preferences = await self.preferences_service.get_user_preferences(notification.user_id)
            contact_info = self._extract_contact_info(user_preferences)
            
            # Try preferred channels first
            for channel in preferred_channels:
                if await self._is_channel_available(channel, user_preferences):
                    success = await self._deliver_via_channel(notification, channel, contact_info)
                    results[channel] = success
                    
                    if success:
                        delivered = True
                        logger.info(
                            "notification.delivered_via_preferred",
                            notification_id=str(notification.id),
                            channel=channel.value,
                            user_id=str(notification.user_id)
                        )
                        break
                else:
                    results[channel] = False
                    logger.debug(
                        "notification.channel_unavailable",
                        notification_id=str(notification.id),
                        channel=channel.value
                    )
            
            # Try fallback channels if preferred failed
            if not delivered and fallback_channels:
                for channel in fallback_channels:
                    if channel not in results and await self._is_channel_available(channel, user_preferences):
                        success = await self._deliver_via_channel(notification, channel, contact_info)
                        results[channel] = success
                        
                        if success:
                            delivered = True
                            logger.info(
                                "notification.delivered_via_fallback",
                                notification_id=str(notification.id),
                                channel=channel.value,
                                user_id=str(notification.user_id)
                            )
                            break
            
            # Log final delivery status
            if delivered:
                notification.mark_as_sent()
                logger.info(
                    "notification.delivery_successful",
                    notification_id=str(notification.id),
                    channels_tried=list(results.keys()),
                    successful_channels=[k.value for k, v in results.items() if v]
                )
            else:
                notification.mark_as_failed("All delivery channels failed")
                logger.error(
                    "notification.delivery_failed",
                    notification_id=str(notification.id),
                    channels_tried=list(results.keys()),
                    user_id=str(notification.user_id)
                )
            
            return results
            
        except Exception as e:
            logger.error(
                "notification.delivery_error",
                notification_id=str(notification.id),
                error=str(e)
            )
            notification.mark_as_failed(f"Delivery error: {str(e)}")
            return {channel: False for channel in preferred_channels}
    
    async def get_optimal_delivery_time(
        self, 
        user_id: UUID, 
        timezone: Optional[str] = None
    ) -> datetime:
        """
        Get optimal delivery time for user based on preferences and timezone.
        
        Args:
            user_id: User ID
            timezone: User's timezone (optional)
            
        Returns:
            Optimal delivery time
        """
        try:
            # Get user preferences
            preferences = await self.preferences_service.get_user_preferences(user_id)
            
            # Use user's timezone if available
            user_timezone = timezone or preferences.get("timezone", "UTC")
            
            # Get quiet hours
            quiet_start = preferences.get("quiet_hours_start")
            quiet_end = preferences.get("quiet_hours_end")
            
            now = datetime.utcnow()
            optimal_time = now
            
            # If we have quiet hours defined, check if we're in them
            if quiet_start and quiet_end:
                current_time = now.time()
                
                # Simple check - in real implementation would handle timezone conversion
                if self._is_in_quiet_hours(current_time, quiet_start, quiet_end):
                    # Schedule for after quiet hours
                    optimal_time = self._get_next_available_time(now, quiet_end)
            
            logger.debug(
                "notification.optimal_delivery_time_calculated",
                user_id=str(user_id),
                optimal_time=optimal_time.isoformat(),
                timezone=user_timezone
            )
            
            return optimal_time
            
        except Exception as e:
            logger.error(
                "notification.optimal_time_calculation_failed",
                user_id=str(user_id),
                error=str(e)
            )
            return datetime.utcnow()
    
    async def batch_deliver(self, notifications: List[Notification]) -> Dict[UUID, Dict[str, Any]]:
        """
        Deliver multiple notifications efficiently.
        
        Args:
            notifications: List of notifications to deliver
            
        Returns:
            Dict mapping notification IDs to delivery results
        """
        results = {}
        successful = 0
        failed = 0
        
        for notification in notifications:
            try:
                # Get user's preferred channels
                preferred_channels = await self._get_user_preferred_channels(notification.user_id)
                fallback_channels = [DeliveryChannel.WEBSOCKET]  # Always try WebSocket as fallback
                
                # Deliver notification
                delivery_results = await self.deliver_notification(
                    notification, preferred_channels, fallback_channels
                )
                
                # Record results
                delivery_successful = any(delivery_results.values())
                results[notification.id] = {
                    "success": delivery_successful,
                    "channels": delivery_results,
                    "timestamp": datetime.utcnow().isoformat()
                }
                
                if delivery_successful:
                    successful += 1
                else:
                    failed += 1
                    
            except Exception as e:
                failed += 1
                results[notification.id] = {
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                logger.error(
                    "notification.batch_delivery_failed",
                    notification_id=str(notification.id),
                    error=str(e)
                )
        
        logger.info(
            "notification.batch_delivery_completed",
            total=len(notifications),
            successful=successful,
            failed=failed
        )
        
        return results
    
    async def _deliver_via_channel(
        self, 
        notification: Notification, 
        channel: DeliveryChannel, 
        contact_info: Dict[str, Any]
    ) -> bool:
        """
        Deliver notification via specific channel.
        
        Args:
            notification: Notification to deliver
            channel: Delivery channel
            contact_info: User's contact information
            
        Returns:
            bool: True if delivery successful
        """
        try:
            if channel == DeliveryChannel.WEBSOCKET:
                # Handle WebSocket delivery directly
                message = {
                    "id": str(notification.id),
                    "type": notification.type.value,
                    "content": notification.content,
                    "subject": notification.subject,
                    "timestamp": datetime.utcnow().isoformat(),
                    "priority": notification.priority.value
                }
                return await self.websocket_manager.send_to_user(notification.user_id, message)
            
            elif channel in self.senders:
                # Use registered sender for the channel
                sender = self.senders[channel]
                return await sender.send(notification, contact_info)
            
            else:
                logger.warning(
                    "notification.unsupported_channel",
                    channel=channel.value,
                    notification_id=str(notification.id)
                )
                return False
                
        except Exception as e:
            logger.error(
                "notification.channel_delivery_failed",
                channel=channel.value,
                notification_id=str(notification.id),
                error=str(e)
            )
            return False
    
    async def _is_channel_available(self, channel: DeliveryChannel, user_preferences: Dict[str, Any]) -> bool:
        """Check if delivery channel is available for user."""
        # Check user preferences
        channel_enabled = await self.preferences_service.is_channel_enabled(
            UUID(user_preferences.get("user_id")), channel
        )
        
        if not channel_enabled:
            return False
        
        # Check if sender is available
        if channel == DeliveryChannel.WEBSOCKET:
            return True  # WebSocket is always available
        
        return channel in self.senders
    
    async def _get_user_preferred_channels(self, user_id: UUID) -> List[DeliveryChannel]:
        """Get user's preferred delivery channels."""
        try:
            preferred_channels = await self.preferences_service.get_preferred_channels(user_id)
            return preferred_channels
        except Exception as e:
            logger.warning(
                "notification.preferred_channels_failed",
                user_id=str(user_id),
                error=str(e)
            )
            # Default fallback channels
            return [DeliveryChannel.EMAIL, DeliveryChannel.WEBSOCKET]
    
    def _extract_contact_info(self, user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """Extract contact information from user preferences."""
        return {
            "email": user_preferences.get("email"),
            "phone": user_preferences.get("phone_number"),
            "push_token": user_preferences.get("push_token"),
            "timezone": user_preferences.get("timezone", "UTC")
        }
    
    def _is_in_quiet_hours(self, current_time, quiet_start, quiet_end) -> bool:
        """Check if current time is within quiet hours."""
        # Simple implementation - would be more sophisticated in real system
        if quiet_start <= quiet_end:
            return quiet_start <= current_time <= quiet_end
        else:
            # Quiet hours span midnight
            return current_time >= quiet_start or current_time <= quiet_end
    
    def _get_next_available_time(self, current_time: datetime, quiet_end) -> datetime:
        """Get next available delivery time after quiet hours."""
        # Simple implementation
        return current_time + timedelta(hours=1)
    
    async def get_delivery_stats(self) -> Dict[str, Any]:
        """Get delivery statistics."""
        try:
            # Get WebSocket connection stats
            websocket_connections = self.websocket_manager.get_active_connections()
            
            # Count available channels
            available_channels = list(self.senders.keys())
            
            stats = {
                "available_channels": [channel.value for channel in available_channels],
                "websocket_connections": websocket_connections,
                "total_senders": len(self.senders),
                "service_health": "healthy"
            }
            
            logger.debug("notification.delivery_stats_retrieved", stats=stats)
            return stats
            
        except Exception as e:
            logger.error("notification.delivery_stats_failed", error=str(e))
            return {"error": str(e), "service_health": "unhealthy"}